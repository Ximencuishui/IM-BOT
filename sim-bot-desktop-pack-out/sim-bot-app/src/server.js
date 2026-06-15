import http from 'http';
import express from 'express';
import cors from 'cors';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { openDatabase, seedSuperAdmin, upsertSuperAdminUser } from './db/database.js';
import { hashPassword } from './auth/password.js';
import { createApiRouter } from './api/routes.js';
import { createDataBackupService } from './services/data_backup.js';
import { startTcpGateway } from './tcp/gateway.js';
import { createHookClient } from './hook/client.js';
import { ensureInboundOnStartup, startTrayHeartbeatLoop } from './bot/tray_heartbeat.js';
import { loadRuntimeEnv } from './util/load_runtime_env.js';
import { buildHookInjectConfig } from './hook/inject_config.js';
import { ensureHookInjectConfigApplied } from './hook/inject_sync.js';
import { normalizeHookInboundPayload } from './hook/recv_normalize.js';
import { dispatchInboundMessage } from './tcp/gateway.js';
import { createSidecarLogger } from './util/logger.js';
import { logInboundDispatchResult } from './util/log_recv.js';
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = process.env.SIM_BOT_ROOT
  ? path.resolve(process.env.SIM_BOT_ROOT)
  : path.join(__dirname, '..');
loadRuntimeEnv(PROJECT_ROOT);

const logger = createSidecarLogger();

async function main() {
  const TCP_HOST = process.env.TCP_HOST || '0.0.0.0';
  const TCP_PORT = Number(process.env.TCP_PORT || 61108);
  const HTTP_HOST = process.env.HTTP_HOST || '0.0.0.0';
  const HTTP_PORT = Number(process.env.HTTP_PORT || 3000);
  const HOOK_CALLBACK_PORT = Number(process.env.HOOK_CALLBACK_PORT || 0);
  const SQLITE_PATH = process.env.SQLITE_PATH || path.join(__dirname, '../data/sim_bot.db');
  const JWT_SECRET = process.env.JWT_SECRET || 'dev-secret-change-me';
  const PUBLIC_KEY =
    process.env.ACTIVATION_PUBLIC_KEY_PATH || path.join(__dirname, '../keys/activation_public.pem');
  const HOOK_BASE = process.env.HOOK_API_BASE || 'http://127.0.0.1:19088';
  const HOOK_TOKEN = process.env.HOOK_API_TOKEN || '';
  const hookInjectCfg = buildHookInjectConfig(PROJECT_ROOT);
  if (!process.env.HOOK_CALLBACK_URL) {
    process.env.HOOK_CALLBACK_URL = hookInjectCfg.http_callback_url;
  }
  if (!process.env.HOOK_RECEIVE_MODE) {
    process.env.HOOK_RECEIVE_MODE = hookInjectCfg.recivemode;
  }
  logger.info(
    `[Hook] 入站模式=${hookInjectCfg.recivemode} 回调=${hookInjectCfg.http_callback_url} TCP=${hookInjectCfg.tcp_ip}:${hookInjectCfg.tcp_port}`
  );

  const db = await openDatabase(SQLITE_PATH);
  const sqliteResolved = path.resolve(SQLITE_PATH);
  logger.info(`SQLite 主库: ${sqliteResolved}（群绑定、产品授权、订单等均写入此文件）`);

  ensureInboundOnStartup(db, logger);

  const flushDbToDisk = () => {
    if (typeof db.persist === 'function') {
      try {
        db.persist();
      } catch (e) {
        logger.warn('[db] 退出前刷盘失败:', e?.message || e);
      }
    }
  };
  process.once('SIGINT', () => {
    flushDbToDisk();
    process.exit(0);
  });
  process.once('SIGTERM', () => {
    flushDbToDisk();
    process.exit(0);
  });

  seedSuperAdmin(db, 'admin', hashPassword('admin123'));
  logger.info('默认超级管理员: admin / admin123 （请在「系统运维 → 账号管理」尽快修改口令）');

  if (process.env.DEV_SUPER_ENABLE === '1') {
    const devUser = String(process.env.DEV_SUPER_USERNAME || '').normalize('NFKC').trim().slice(0, 64);
    const devPass = process.env.DEV_SUPER_PASSWORD != null ? String(process.env.DEV_SUPER_PASSWORD) : '';
    const devPassOk = devPass.length >= 8 && devPass.length <= 256;
    if (!devUser || !/^[\w.-]+$/i.test(devUser)) {
      logger.error(
        '[开发者账号] DEV_SUPER_ENABLE=1 需要合法的 DEV_SUPER_USERNAME（仅字母、数字、下划线、句点与横线，至少 1 字符）'
      );
      process.exit(1);
    }
    if (!devPassOk) {
      logger.error('[开发者账号] DEV_SUPER_PASSWORD 必填，长度 8～256，且用户名不能含空格');
      process.exit(1);
    }
    try {
      upsertSuperAdminUser(db, devUser, hashPassword(devPass));
      if (typeof db.persist === 'function') db.persist();
      logger.warn(
        '[开发者账号] 已与默认 admin 同属超级管理员权限；密钥仅保存在本机 .env，切勿随安装包对用户分发 DEV_SUPER_*'
      );
      logger.warn(`[开发者账号] 登录用户名: ${devUser}（口令见 .env，不在日志中打印）`);
    } catch (e) {
      logger.error('[开发者账号] 写入失败:', e?.message || e);
      process.exit(1);
    }
  }

  if (process.env.SKIP_PRODUCT_SETUP === '1') {
    logger.warn(
      '[产品授权] SKIP_PRODUCT_SETUP=1，已跳过安装授权门禁；正式环境切勿开启。安装授权码由 scripts/gen-product-setup-license.mjs 签发。'
    );
  } else {
    logger.info(
      '[产品授权] 未完成安装授权时控制台仅开放 /api/setup/*；请将 scripts/gen-product-setup-license.mjs 生成的安装码交给用户。'
    );
  }

  const BACKUP_DEFAULT_DIR = process.env.BACKUP_DIR || path.join(path.dirname(SQLITE_PATH), 'backups');
  const BACKUP_RETENTION_DAYS = Number(process.env.BACKUP_RETENTION_DAYS || 7);
  const BACKUP_HOUR_CFG = Number(process.env.BACKUP_HOUR ?? 3);
  const dataBackupService = createDataBackupService({
    db,
    sqlitePath: SQLITE_PATH,
    defaultBackupDir: BACKUP_DEFAULT_DIR,
    retentionDays: BACKUP_RETENTION_DAYS,
    backupHour: BACKUP_HOUR_CFG,
    logger,
  });
  dataBackupService.startScheduler();
  logger.info(
    `数据备份：默认目录 ${BACKUP_DEFAULT_DIR}（可在运维页改路径）；每日 ${BACKUP_HOUR_CFG}:00（进程本地时间）一次；保留最近 ${BACKUP_RETENTION_DAYS} 天`
  );

  const hook = createHookClient(HOOK_BASE, HOOK_TOKEN);
  hook.healthProbe().then((r) => {
    if (r.ok) logger.info('Hook 控制面探测成功');
    else logger.warn('Hook 控制面不可达（课题可忽略）:', r.error);
  });

  const app = express();
  app.use(cors());
  app.use(express.text({ type: ['text/*', 'application/*+json'], limit: '4mb' }));
  app.use(express.json({ limit: '2mb' }));
  const recvText = express.text({ type: '*/*', limit: '4mb' });
  const handleHookRecvMsg = async (req, res) => {
    try {
      const payload = normalizeHookInboundPayload(req.body);
      if (!payload) {
        return res.status(200).json({ errCode: 0, code: 0, msg: 'ok' });
      }
      const result = await dispatchInboundMessage(payload, { db, logger, hookClient: hook });
      logInboundDispatchResult(result, logger, 'recvMsg-http');
      return res.status(200).json({ errCode: 0, code: 0, msg: 'ok' });
    } catch (e) {
      logger.warn('[recvMsg] error', e?.message || e);
      return res.status(200).json({ errCode: 0, code: 0, msg: 'ok' });
    }
  };
  app.post('/recvMsg', recvText, handleHookRecvMsg);
  app.use(
    '/api',
    createApiRouter({
      db,
      jwtSecret: JWT_SECRET,
      publicKeyPath: PUBLIC_KEY,
      logger,
      hookClient: hook,
      dataBackupService,
      sqlitePath: SQLITE_PATH,
    })
  );
  const legacyPublic = path.join(__dirname, '../public');
  const adminDist = path.join(__dirname, '../admin/dist');
  const adminIndex = path.join(adminDist, 'index.html');

  app.use(express.static(legacyPublic));
  if (fs.existsSync(adminIndex)) {
    app.use('/admin', express.static(adminDist));
    app.get('/', (_req, res) => res.redirect('/admin/'));
    app.get('/admin/*', (_req, res) => res.sendFile(adminIndex));
  } else {
    logger.warn(
      '未找到 admin/dist：请在本机执行 npm run admin:build，否则只能打开旧版 public/admin.html（无「合集管理」等新界面）'
    );
    app.get('/', (_req, res) => res.redirect('/admin.html'));
  }

  const httpServer = http.createServer(app);
  httpServer.on('error', (err) => {
    if (err?.code === 'EADDRINUSE') {
      logger.error(
        `[HTTP] 端口 ${HTTP_PORT} 已被占用（${err.message}）。请关闭其它 Sim Bot / node 实例后重试。`
      );
      process.exit(1);
    }
    logger.error('[HTTP] listen error:', err?.message || err);
    process.exit(1);
  });
  httpServer.listen(HTTP_PORT, HTTP_HOST, () => {
    logger.info(`Admin HTTP http://${HTTP_HOST}:${HTTP_PORT}`);
  });

  if (
    Number.isFinite(HOOK_CALLBACK_PORT) &&
    HOOK_CALLBACK_PORT > 0 &&
    HOOK_CALLBACK_PORT !== HTTP_PORT
  ) {
    const hookCbServer = http.createServer(app);
    hookCbServer.on('error', (err) => {
      logger.warn(
        `[HTTP] Hook 回调端口 ${HOOK_CALLBACK_PORT} 不可用（${err?.message || err}），仅影响 DLL HTTP 回调。`
      );
    });
    hookCbServer.listen(HOOK_CALLBACK_PORT, HTTP_HOST, () => {
      logger.info(`Hook HTTP 回调 http://${HTTP_HOST}:${HOOK_CALLBACK_PORT}/api/recvMsg`);
    });
  }

  startTcpGateway({ host: TCP_HOST, port: TCP_PORT, db, logger, hookClient: hook });

  startTrayHeartbeatLoop(db, logger, { hookClient: hook, projectRoot: PROJECT_ROOT });

  /** 延迟后台注入：spawnSync 会占满主线程，避免刚启动时浏览器访问 3000 超时/拒绝 */
  setTimeout(() => {
    void (async () => {
      const injResult = await ensureHookInjectConfigApplied(db, logger, {
        projectRoot: PROJECT_ROOT,
        hookClient: hook,
      });
      if (injResult?.ok && hook?.probeLoginWxid) {
        const { probeAndPersistLoginWxid } = await import('./db/wechat_login_store.js');
        const probe = await probeAndPersistLoginWxid(db, hook);
        if (probe.ok) logger.info(`[wechat-inject] 已识别登录 wxid=${probe.wxid}`);
        else logger.warn(`[wechat-inject] 注入后仍未取得 wxid: ${probe.message || 'unknown'}`);
      }
    })().catch((e) => logger.warn('[wechat-inject] 启动注入任务异常:', e?.message || e));
  }, 2000);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});

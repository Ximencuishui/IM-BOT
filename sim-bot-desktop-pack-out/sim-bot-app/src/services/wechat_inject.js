import { spawnSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import {
  appendBotWorkLog,
  BOT_RUNTIME_STARTED_KEY,
  getBotInboundEnabled,
  setBotInboundEnabled,
  syncBotRuntimeStartedAt,
} from '../bot/runtime_store.js';
import { buildHookInjectConfig } from '../hook/inject_config.js';
import { invalidateHookRuntimeCache } from '../hook/hook_runtime.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/**
 * 与「高级设置 → 查找微信并注入」相同：同步执行 launch-wechat-hook.mjs，继承当前 Node 进程环境。
 * @param {object} opts
 * @param {import('../db/database.js').Database} opts.db
 * @param {string} [opts.projectRoot]
 * @param {object} [opts.hookClient]
 * @param {object} [opts.logger]
 */
/**
 * @param {object} opts
 * @param {boolean} [opts.bootstrapInject] 显式覆盖 WECHAT_BOOTSTRAP_INJECT
 * @param {boolean} [opts.quitBeforeInject] 显式覆盖 WECHAT_QUIT_BEFORE_INJECT（自动看门狗/心跳应传 false）
 */
export async function runWechatHookInject({
  db,
  projectRoot,
  hookClient,
  logger = console,
  bootstrapInject: bootstrapInjectOpt,
  quitBeforeInject: quitBeforeInjectOpt,
} = {}) {
  if (process.platform !== 'win32') {
    return { ok: false, error: '微信注入仅支持在 Windows 上执行' };
  }
  const root = path.resolve(
    projectRoot || process.env.SIM_BOT_ROOT || path.join(__dirname, '..', '..')
  );
  const scriptPath = path.join(root, 'scripts', 'launch-wechat-hook.mjs');
  if (!fs.existsSync(scriptPath)) {
    return { ok: false, error: '未找到 scripts/launch-wechat-hook.mjs' };
  }

  const inj = buildHookInjectConfig(root);
  const bootstrapInject =
    bootstrapInjectOpt != null
      ? Boolean(bootstrapInjectOpt)
      : process.env.WECHAT_BOOTSTRAP_INJECT === '1';
  const quitBeforeInject =
    quitBeforeInjectOpt != null
      ? Boolean(quitBeforeInjectOpt)
      : process.env.WECHAT_QUIT_BEFORE_INJECT === '1' ||
        (bootstrapInject && process.env.WECHAT_QUIT_BEFORE_INJECT !== '0');
  const sub = spawnSync(process.execPath, [scriptPath], {
    cwd: root,
    encoding: 'utf8',
    env: {
      ...process.env,
      SIM_BOT_ROOT: root,
      WECHAT_BOOTSTRAP_INJECT: bootstrapInject ? '1' : '0',
      WECHAT_QUIT_BEFORE_INJECT: quitBeforeInject ? '1' : '0',
      HOOK_RECEIVE_MODE: process.env.HOOK_RECEIVE_MODE || inj.recivemode,
      HOOK_CALLBACK_URL: process.env.HOOK_CALLBACK_URL || inj.http_callback_url,
    },
    timeout: 600_000,
    maxBuffer: 20 * 1024 * 1024,
    windowsHide: true,
  });

  const stdout = (sub.stdout || '').trim();
  const stderr = (sub.stderr || '').trim();

  if (sub.error) {
    logger.warn?.('[wechat-inject] spawn', sub.error);
    return {
      ok: false,
      error: sub.error.message || String(sub.error),
      stdout,
      stderr,
    };
  }
  if (sub.status !== 0) {
    return {
      ok: false,
      error: `注入脚本退出码 ${sub.status}`,
      stdout,
      stderr,
    };
  }

  const wasInboundOn = getBotInboundEnabled(db);
  setBotInboundEnabled(db, true);
  appendBotWorkLog(db, 'info', '微信客户端注入完成', null);
  if (!wasInboundOn) {
    syncBotRuntimeStartedAt(db, true);
    appendBotWorkLog(db, 'info', '机器人入站处理已启动', null);
  }
  const on = getBotInboundEnabled(db);
  let started_at = null;
  if (on) {
    const row = db.prepare('SELECT value FROM app_settings WHERE key = ?').get(BOT_RUNTIME_STARTED_KEY);
    started_at = row?.value != null ? String(row.value).trim() : null;
  }
  let login_wxid = '';
  if (hookClient) {
    const { probeAndPersistLoginWxid } = await import('../db/wechat_login_store.js');
    const loginProbe = await probeAndPersistLoginWxid(db, hookClient);
    if (loginProbe.ok && loginProbe.wxid) login_wxid = loginProbe.wxid;
  }
  if (typeof db.persist === 'function') db.persist();
  invalidateHookRuntimeCache();

  return {
    ok: true,
    log: stdout,
    stderr: stderr || undefined,
    inbound_enabled: on,
    started_at,
    login_wxid,
  };
}

import express from 'express';
import net from 'net';
import multer from 'multer';
import path from 'path';
import { fileURLToPath } from 'url';
import { signToken, verifyToken } from '../auth/jwt.js';
import { verifyPassword, hashPassword } from '../auth/password.js';
import {
  verifyActivationCode,
  activationFingerprint,
  assertPayloadRedeemDeadline,
  getActivationCardSecret,
} from '../auth/activation.js';
import fs from 'fs';
import { isWeixinProcessRunning } from '../util/weixin_process.js';
import { importMainDatabaseFromBuffer, reseedGlobalCollections } from '../db/database.js';
import { extendWxGroupExpiresAt, upsertWxGroupBound } from '../db/wx_groups_store.js';
import {
  executeConfiguredCommand,
  executeFormulaTest,
  validateFormulaPipeline,
  cmdRouteDisplayLabel,
  stripWeChatAtPrefix,
  listOrderLineStructuralPreview,
} from '../commands/engine.js';
import {
  getBotInboundEnabled,
  setBotInboundEnabled,
  syncBotRuntimeStartedAt,
  appendBotWorkLog,
  BOT_RUNTIME_STARTED_KEY,
} from '../bot/runtime_store.js';
import {
  collectTrayHeartbeat,
  setBotInboundUserPaused,
  isBotInboundUserPaused,
} from '../bot/tray_heartbeat.js';
import { dispatchInboundMessage, getInboundRecvStats } from '../tcp/gateway.js';
import { normalizeHookInboundPayload } from '../hook/recv_normalize.js';
import { hookRawPayloadSummary } from '../util/logger.js';
import { logInboundDispatchResult } from '../util/log_recv.js';
import { runWechatHookInject } from '../services/wechat_inject.js';
import { formatSqliteUtcForDisplay } from '../util/datetime.js';
import {
  computeSpecialCodeRisk,
  rustEngineAvailable,
} from '../commands/rust_bridge.js';
import {
  listAliasConfig,
  upsertAliasConfig,
  deleteAliasConfig,
  getRobotConfig,
  upsertRobotConfig,
  verifyRobotConfigRow,
  listGroupsNearingExpiry,
  isRobotLicenseValid,
  redeemGroupCardCipher,
  redeemRobotCardCipher,
  seedRobotLicenseDays,
  recordCardHistory,
  applyPendingInstallRobotLicense,
  getPrdWechatProfile,
  verifyGroupWhitelistRow,
  listPrdGroups,
  listPrdGroupDeskRows,
  isGroupServiceValid,
} from '../db/prd_store.js';
import { importAmountUnitAliasesToAliasConfig } from '../commands/alias_resolver.js';
import { invalidateParseCaches } from '../commands/parse_cache.js';
import {
  getSetupWechatLoginStatus,
  getWechatLoginWxid,
  probeAndPersistLoginWxid,
} from '../db/wechat_login_store.js';

const __routesDir = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.join(__routesDir, '..', '..');

export function createApiRouter({
  db,
  jwtSecret,
  publicKeyPath,
  logger,
  hookClient,
  dataBackupService = null,
  sqlitePath = null,
}) {
  const r = express.Router();

  const isLoopback = (req) => {
    const ip = String(req.ip || req.socket?.remoteAddress || '').replace(/^::ffff:/, '');
    return ip === '127.0.0.1' || ip === '::1' || ip === 'localhost';
  };

  function loadActivationPem() {
    return publicKeyPath && fs.existsSync(publicKeyPath)
      ? fs.readFileSync(publicKeyPath, 'utf8')
      : null;
  }

  function resolveBotWxidForLicense() {
    const login = getWechatLoginWxid(db);
    if (login) return String(login).trim();
    const row = getRobotConfig(db);
    return String(row?.wxid || '').trim();
  }

  async function buildSetupWechatLoginResponse(refresh = false) {
    let hook_probe_ok;
    if (refresh) {
      const probe = await probeAndPersistLoginWxid(db, hookClient);
      hook_probe_ok = Boolean(probe.ok);
    }
    const robot = getRobotConfig(db);
    const body = getSetupWechatLoginStatus(db, { robotWxid: robot?.wxid || '' });
    const prof = getPrdWechatProfile(db);
    body.nickname = prof.nickname || '';
    body.avatar_url = prof.avatar_url || '';
    if (prof.login_wxid) body.login_wxid = prof.login_wxid;
    if (hook_probe_ok !== undefined) body.hook_probe_ok = hook_probe_ok;
    return body;
  }

  function verifyLicenseCode(code, wxid) {
    return verifyActivationCode(
      {
        publicKeyPem: loadActivationPem(),
        cardSecret: getActivationCardSecret(),
        wxid: String(wxid || '').trim(),
      },
      String(code || '').trim()
    );
  }

  const isLocalTcpPortOpen = (port, timeoutMs = 500) =>
    new Promise((resolve) => {
      const host = '127.0.0.1';
      const socket = net.connect({ host, port });
      const finish = (ok) => {
        socket.destroy();
        resolve(ok);
      };
      socket.setTimeout(timeoutMs);
      socket.once('connect', () => finish(true));
      socket.once('timeout', () => finish(false));
      socket.once('error', () => finish(false));
    });

  /** Tauri 托盘 / 顶栏心跳（仅本机 loopback）：检测微信·Hook·入站，并维持入站开启 */
  r.get('/health/tray', async (req, res) => {
    if (!isLoopback(req)) return res.status(403).json({ error: 'forbidden' });
    const sync = String(req.query.sync || '1') !== '0';
    const body = await collectTrayHeartbeat(db, { syncInbound: sync });
    res.json({ ...body, ...getInboundRecvStats(db) });
  });

  /** 与「高级设置 → 查找微信并注入」相同逻辑；供桌面壳 loopback 自动注入（不关微信，仅 PID 热注入） */
  r.post('/bot/wechat-inject', async (req, res) => {
    if (!isLoopback(req)) return res.status(403).json({ error: 'forbidden' });
    try {
      const result = await runWechatHookInject({
        db,
        projectRoot: PROJECT_ROOT,
        hookClient,
        logger,
        bootstrapInject: true,
        quitBeforeInject: false,
      });
      if (!result.ok) {
        return res.status(500).json(result);
      }
      res.json(result);
    } catch (e) {
      logger.error('[api/bot/wechat-inject]', e);
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  });

  r.get('/admin/prd/rust-status', auth, requireRole('super'), (_req, res) => {
    res.json({
      rust_prd_enabled: process.env.USE_RUST_PRD === '1',
      rust_engine_main: process.env.USE_RUST_PRD === '1' && process.env.USE_RUST_ENGINE !== '0',
      rust_cli_available: rustEngineAvailable(),
    });
  });

  r.post('/admin/prd/compute-risk', auth, requireRole('super', 'group_admin'), (req, res) => {
    const total = Number(req.body?.total_special_amount ?? req.body?.totalSpecialAmount ?? 0);
    const bet = Number(req.body?.bet_on_number ?? req.body?.betOnNumber ?? 0);
    const water = Number(req.body?.water_rate ?? req.body?.waterRate ?? 0.04);
    const odds = Number(req.body?.payout_odds ?? req.body?.payoutOdds ?? 47);
    const profit = computeSpecialCodeRisk({
      totalSpecialAmount: total,
      betOnNumber: bet,
      waterRate: water,
      payoutOdds: odds,
    });
    res.json({ profit, engine: rustEngineAvailable() ? 'rust' : 'node' });
  });

  const sqliteImportUpload = multer({
    storage: multer.memoryStorage(),
    limits: { fileSize: 80 * 1024 * 1024 },
  });

  /** Hook DLL HTTP 回调（无 JWT，与注入配置 http_callback_url 一致） */
  r.post('/recvMsg', express.text({ type: '*/*', limit: '4mb' }), async (req, res) => {
    try {
      let payload = normalizeHookInboundPayload(req.body);
      if (!payload) {
        return res.status(200).json({ errCode: 0, code: 0, msg: 'ok' });
      }
      const result = await dispatchInboundMessage(payload, { db, logger, hookClient });
      logInboundDispatchResult(result, logger, 'recvMsg');
      return res.status(200).json({ errCode: 0, code: 0, msg: 'ok' });
    } catch (e) {
      logger.warn('[recvMsg] error', e?.message || e);
      return res.status(200).json({ errCode: 0, code: 0, msg: 'ok' });
    }
  });

  const SETUP_KEYS = {
    PRODUCT_DONE: 'product_setup_completed',
    BONUS_AVAIL: 'install_group_bonus_available',
    BONUS_DAYS: 'install_group_bonus_days',
  };

  const skipProductSetup = () => process.env.SKIP_PRODUCT_SETUP === '1';

  function getAppSetting(key) {
    const row = db.prepare('SELECT value FROM app_settings WHERE key = ?').get(key);
    return row ? row.value : null;
  }

  function setAppSetting(key, value) {
    db.prepare(
      `INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, datetime('now'))
       ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = datetime('now')`
    ).run(key, String(value));
  }

  function isProductSetupCompleted() {
    if (skipProductSetup()) return true;
    return getAppSetting(SETUP_KEYS.PRODUCT_DONE) === '1';
  }

  r.get('/setup/wechat-login', async (req, res) => {
    try {
      const refresh = String(req.query.refresh || '') === '1';
      res.json(await buildSetupWechatLoginResponse(refresh));
    } catch (e) {
      logger.error('[setup/wechat-login]', e);
      res.status(500).json({
        wxid: '',
        login_wxid: '',
        robot_wxid: '',
        wechat_process_running: isWeixinProcessRunning(),
        status: 'wechat_running_no_wxid',
        error: String(e?.message || e),
      });
    }
  });

  r.get('/setup/status', (_req, res) => {
    if (skipProductSetup()) {
      return res.json({
        setup_required: false,
        skipped: true,
        install_group_bonus_available: getAppSetting(SETUP_KEYS.BONUS_AVAIL) === '1',
        install_group_bonus_days: Number(getAppSetting(SETUP_KEYS.BONUS_DAYS) || '365'),
      });
    }
    const done = getAppSetting(SETUP_KEYS.PRODUCT_DONE) === '1';
    res.json({
      setup_required: !done,
      install_group_bonus_available: getAppSetting(SETUP_KEYS.BONUS_AVAIL) === '1',
      install_group_bonus_days: Number(getAppSetting(SETUP_KEYS.BONUS_DAYS) || '365'),
    });
  });

  r.post('/setup/complete', (req, res) => {
    try {
      if (skipProductSetup()) {
        return res.json({ ok: true, skipped: true });
      }
      if (isProductSetupCompleted()) {
        return res.status(400).json({ error: '已完成初始化' });
      }
      const code = String(req.body?.code || '').trim();
      if (!code) return res.status(400).json({ error: '请填写授权码' });
      const setupWxid = String(req.body?.wxid || resolveBotWxidForLicense() || '').trim();
      const v = verifyLicenseCode(code, setupWxid);
      if (!v.ok) {
        if (v.reason === 'short_code_needs_wxid') {
          return res.status(400).json({
            error: '32 位卡密须绑定本机微信 wxid：请先在下方识别机器码，或由销售端按该 wxid 发卡',
            detail: v.reason,
          });
        }
        const hint =
          v.reason === 'no_card_secret'
            ? '桌面端未配置 ACTIVATION_CARD_SECRET（与发卡端一致）。可在 %APPDATA%\\SimBot\\config.env 设置后重启，或重新打包时写入仓库 .env 中的密钥。'
            : v.reason === 'bad_short_signature'
              ? '32 位卡密与当前 wxid 或密钥不匹配：请确认页面已识别本机 wxid，且发卡时填写的 wxid 一致。'
              : '';
        return res.status(400).json({
          error: hint ? `授权码无效：${hint}` : '授权码无效',
          detail: v.reason,
        });
      }
      const deadline = assertPayloadRedeemDeadline(v.payload);
      if (!deadline.ok) {
        return res.status(400).json({
          error: '该授权码已超过兑换截止时间，无法使用',
          detail: deadline.reason,
        });
      }
      if (v.payload.installation !== true) {
        return res.status(400).json({
          error: '该码不是产品安装授权类型（群月卡请登录后在「群管理」续费，勿用于首次安装页）',
        });
      }
      const fp = activationFingerprint(code);
      try {
        db.prepare('INSERT INTO setup_license_claims (code_fingerprint, raw_payload) VALUES (?, ?)').run(
          fp,
          JSON.stringify(v.payload)
        );
      } catch {
        return res.status(400).json({ error: '该授权码已被使用' });
      }
      const days = Math.min(3660, Math.max(1, Number(v.payload.group_validity_days ?? 365) || 365));
      setAppSetting(SETUP_KEYS.PRODUCT_DONE, '1');
      setAppSetting(SETUP_KEYS.BONUS_AVAIL, '1');
      setAppSetting(SETUP_KEYS.BONUS_DAYS, String(days));
      let robot_license = null;
      if (setupWxid) {
        robot_license = seedRobotLicenseDays(db, {
          wxid: setupWxid,
          days,
          last_card_cipher: code,
        });
        recordCardHistory(db, fp, setupWxid);
      }
      if (typeof db.persist === 'function') db.persist();
      res.json({
        ok: true,
        install_group_bonus_days: days,
        robot_expire_date: robot_license?.expire_date || null,
        expire_display: robot_license?.expire_display || null,
      });
    } catch (e) {
      logger.error('[setup/complete]', e);
      res.status(500).json({ error: String(e?.message || e) });
    }
  });

  /** 未完成安装授权时不开放登录与其它 API（SKIP_PRODUCT_SETUP=1 跳过，便于开发） */
  r.use((req, res, next) => {
    if (skipProductSetup()) return next();
    const p = req.path || '';
    if (p === '/setup/status' || p === '/setup/complete' || p === '/setup/wechat-login') return next();
    if (!isProductSetupCompleted()) {
      return res.status(423).json({ error: '请先完成产品与授权初始化', setup_required: true });
    }
    next();
  });

  function upsertContactProfile(wxid, profile, source) {
    if (!wxid) return;
    db.prepare(
      `INSERT INTO wx_contact_profiles
      (wxid, nick_name, display_name, small_head_url, big_head_url, source, last_seen_at)
      VALUES (?,?,?,?,?,?,datetime('now'))
      ON CONFLICT(wxid) DO UPDATE SET
        nick_name=excluded.nick_name,
        display_name=excluded.display_name,
        small_head_url=excluded.small_head_url,
        big_head_url=excluded.big_head_url,
        source=excluded.source,
        last_seen_at=datetime('now')`
    ).run(
      wxid,
      profile?.nick_name || profile?.nickName || null,
      profile?.display_name || profile?.displayName || null,
      profile?.small_head_url || profile?.smallHeadImgUrl || null,
      profile?.big_head_url || profile?.bigHeadImgUrl || null,
      source || null
    );
  }

  function upsertChatroomCache(room) {
    if (!room?.room_id) return;
    db.prepare(
      `INSERT INTO wx_chatroom_cache
      (room_id, nick_name, remark, small_head_url, big_head_url, owner_wxid, owner_nick, member_count, updated_at)
      VALUES (?,?,?,?,?,?,?,?,datetime('now'))
      ON CONFLICT(room_id) DO UPDATE SET
        nick_name=excluded.nick_name,
        remark=excluded.remark,
        small_head_url=excluded.small_head_url,
        big_head_url=excluded.big_head_url,
        owner_wxid=COALESCE(excluded.owner_wxid, wx_chatroom_cache.owner_wxid),
        owner_nick=COALESCE(excluded.owner_nick, wx_chatroom_cache.owner_nick),
        member_count=CASE WHEN excluded.member_count > 0 THEN excluded.member_count ELSE wx_chatroom_cache.member_count END,
        updated_at=datetime('now')`
    ).run(
      room.room_id,
      room.nick_name || null,
      room.remark || null,
      room.small_head_url || null,
      room.big_head_url || null,
      room.owner_wxid || null,
      room.owner_nick || null,
      Number(room.member_count || 0)
    );
  }

  function upsertChatroomMember(roomId, member, ownerWxid) {
    const wxid = member?.wxid || member?.userName || '';
    if (!roomId || !wxid) return;
    db.prepare(
      `INSERT INTO wx_chatroom_members
      (room_id, wxid, nick_name, display_name, small_head_url, big_head_url, inviter_wxid, status, is_owner, updated_at)
      VALUES (?,?,?,?,?,?,?,?,?,datetime('now'))
      ON CONFLICT(room_id, wxid) DO UPDATE SET
        nick_name=excluded.nick_name,
        display_name=excluded.display_name,
        small_head_url=excluded.small_head_url,
        big_head_url=excluded.big_head_url,
        inviter_wxid=excluded.inviter_wxid,
        status=excluded.status,
        is_owner=excluded.is_owner,
        updated_at=datetime('now')`
    ).run(
      roomId,
      wxid,
      member?.nick_name || member?.nickName || null,
      member?.display_name || member?.displayName || null,
      member?.small_head_url || member?.smallHeadImgUrl || null,
      member?.big_head_url || member?.bigHeadImgUrl || null,
      member?.inviter_wxid || member?.inviterUserName || null,
      member?.status ?? null,
      wxid && ownerWxid && wxid === ownerWxid ? 1 : 0
    );
  }

  function auth(req, res, next) {
    const h = req.headers.authorization || '';
    const token = h.startsWith('Bearer ') ? h.slice(7) : null;
    const body = verifyToken(token, jwtSecret);
    if (!body) return res.status(401).json({ error: '未授权' });
    req.user = body;
    next();
  }

  function requireRole(...roles) {
    return (req, res, next) => {
      if (!roles.includes(req.user.role)) return res.status(403).json({ error: '权限不足' });
      next();
    };
  }

  const LOGIN_WINDOW_MS = 15 * 60 * 1000;
  /** 滑动窗口内失败次数达到此值即暂时锁定登录 */
  const LOGIN_FAIL_MAX = 10;
  const LOGIN_LOCK_MS = 15 * 60 * 1000;
  const loginFailBuckets = new Map();

  function getClientIp(req) {
    const xff = req.headers['x-forwarded-for'];
    if (xff && typeof xff === 'string') return String(xff).split(',')[0].trim().slice(0, 128);
    return String(req.socket?.remoteAddress || req.ip || 'unknown').slice(0, 128);
  }

  /** 登录失败计数（仅错误口令等失败计入，成功后清空） */
  function recordLoginFailure(ip) {
    const nowMs = Date.now();
    let st = loginFailBuckets.get(ip) || { failTimes: [], lockedUntil: null };
    if (st.lockedUntil && nowMs < st.lockedUntil) return;
    if (st.lockedUntil && nowMs >= st.lockedUntil) {
      st = { failTimes: [], lockedUntil: null };
    }
    st.failTimes = (st.failTimes || []).filter((t) => nowMs - t < LOGIN_WINDOW_MS);
    st.failTimes.push(nowMs);
    if (st.failTimes.length >= LOGIN_FAIL_MAX) {
      logger.warn('[auth/login] brute_force_lock', {
        ip,
        fails_in_window: st.failTimes.length,
        lock_min: LOGIN_LOCK_MS / 60000,
      });
      st.lockedUntil = nowMs + LOGIN_LOCK_MS;
      st.failTimes = [];
    }
    loginFailBuckets.set(ip, st);
  }

  function clearLoginFailure(ip) {
    loginFailBuckets.delete(ip);
  }

  r.post('/auth/login', (req, res) => {
    const ip = getClientIp(req);
    const nowMs = Date.now();
    try {
      const st = loginFailBuckets.get(ip);
      if (st?.lockedUntil && nowMs < st.lockedUntil) {
        const retryAfterSec = Math.ceil((st.lockedUntil - nowMs) / 1000);
        logger.warn('[auth/login] temporarily_locked', { ip, retry_after_sec: retryAfterSec });
        return res.status(429).json({
          error: '登录尝试次数过多，请稍后再试',
          retry_after_sec: retryAfterSec,
        });
      }

      const rawUser = req.body?.username;
      const rawPass = req.body?.password;
      const username =
        typeof rawUser === 'string' ? rawUser.normalize('NFKC').trim() : '';
      const password = typeof rawPass === 'string' ? rawPass : '';

      if (!username || !password) {
        return res.status(400).json({ error: '请输入用户名和密码' });
      }
      if (username.length > 64 || password.length > 256) {
        logger.warn('[auth/login] rejected_bad_length', { ip, username_len: username.length });
        return res.status(400).json({ error: '用户名或密码长度无效' });
      }

      let row;
      try {
        row = db.prepare('SELECT id, username, password_hash, role FROM users WHERE username = ?').get(username);
      } catch (e) {
        logger.error('[auth/login] db_query failed', e);
        return res.status(500).json({ error: '服务器繁忙，请稍后再试' });
      }

      if (!row || !verifyPassword(password, row.password_hash)) {
        recordLoginFailure(ip);
        return res.status(401).json({ error: '用户名或密码错误' });
      }

      clearLoginFailure(ip);

      let token;
      try {
        token = signToken(
          { uid: row.id, username: row.username, role: row.role },
          jwtSecret
        );
      } catch (e) {
        logger.error('[auth/login] token_sign_failed', { ip, uid: row.id, err: e?.message });
        return res.status(500).json({ error: '服务器繁忙，请稍后再试' });
      }

      logger.info('[auth/login] ok', { username: row.username, role: row.role, ip });
      res.json({ token, user: { id: row.id, username: row.username, role: row.role } });
    } catch (e) {
      logger.error('[auth/login] unhandled', {
        ip,
        message: e?.message,
        stack: e?.stack,
      });
      res.status(500).json({ error: '服务器繁忙，请稍后再试' });
    }
  });

  r.get('/me', auth, (req, res) => {
    res.json({ user: req.user });
  });

  /** 超级管理：群绑定 */
  r.post(
    '/admin/groups',
    auth,
    requireRole('super'),
    (req, res) => {
      const { wx_group_id, name } = req.body || {};
      let { expires_at } = req.body || {};
      if (!wx_group_id) return res.status(400).json({ error: '缺少 wx_group_id' });
      const trimOpt = (x) => {
        if (x == null) return null;
        const s = String(x).trim();
        return s === '' ? null : s;
      };
      const cap = (t, n) => (!t || t.length <= n ? t : t.slice(0, n));
      const manual_owner = cap(trimOpt(req.body?.manual_owner), 256);
      try {
        const eaManual = expires_at != null && String(expires_at).trim() !== '' ? String(expires_at).trim() : null;
        const prior = db.prepare('SELECT expires_at FROM wx_groups WHERE wx_group_id = ?').get(wx_group_id);
        let expiresFinal = eaManual;
        let consumeBonus = false;
        if (!eaManual && getAppSetting(SETUP_KEYS.BONUS_AVAIL) === '1' && !prior?.expires_at) {
          consumeBonus = true;
          const d = Math.min(3660, Math.max(1, Number(getAppSetting(SETUP_KEYS.BONUS_DAYS) || '365') || 365));
          const t = new Date();
          t.setDate(t.getDate() + d);
          expiresFinal = t.toISOString();
        }
        const upserted = upsertWxGroupBound(db, {
          wx_group_id,
          name: name || null,
          manual_owner,
          expires_at: expiresFinal != null ? expiresFinal : undefined,
        });
        if (consumeBonus) {
          setAppSetting(SETUP_KEYS.BONUS_AVAIL, '0');
        }
        if (typeof db.persist === 'function') db.persist();
        res.json({
          ok: true,
          created: upserted.created,
          expires_at: expiresFinal || null,
          used_install_bonus_year: consumeBonus,
        });
      } catch (e) {
        res.status(400).json({ error: String(e.message) });
      }
    }
  );

  r.get('/admin/groups', auth, requireRole('super', 'group_admin'), (req, res) => {
    if (req.user.role === 'super') {
      const rows = db.prepare('SELECT * FROM wx_groups ORDER BY id DESC').all();
      return res.json({ groups: rows });
    }
    const rows = db
      .prepare('SELECT * FROM wx_groups WHERE group_admin_user_id = ? ORDER BY id DESC')
      .all(req.user.uid);
    res.json({ groups: rows });
  });

  /** 群管理：手动维护群标识、群主说明、备注（仅超管或绑定到该群的 group_admin） */
  r.patch('/admin/groups/:id', auth, requireRole('super', 'group_admin'), (req, res) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id <= 0) return res.status(400).json({ error: '无效的群 id' });
    const row = db.prepare('SELECT * FROM wx_groups WHERE id = ?').get(id);
    if (!row) return res.status(404).json({ error: '群不存在' });
    if (req.user.role !== 'super') {
      const aid = row.group_admin_user_id != null ? Number(row.group_admin_user_id) : null;
      if (aid == null || aid !== Number(req.user.uid)) {
        return res.status(403).json({ error: '无权编辑该群' });
      }
    }
    const trimOpt = (x) => {
      if (x == null) return null;
      const s = String(x).trim();
      return s === '' ? null : s;
    };
    const cap = (t, n) => (!t || t.length <= n ? t : t.slice(0, n));
    const admin_label = cap(trimOpt(req.body?.admin_label), 128);
    const manual_owner = cap(trimOpt(req.body?.manual_owner), 256);
    const admin_remark = cap(trimOpt(req.body?.admin_remark), 2000);
    db.prepare(
      'UPDATE wx_groups SET admin_label = ?, manual_owner = ?, admin_remark = ? WHERE id = ?'
    ).run(admin_label, manual_owner, admin_remark, id);
    const updated = db.prepare('SELECT * FROM wx_groups WHERE id = ?').get(id);
    if (typeof db.persist === 'function') db.persist();
    res.json({ ok: true, group: updated });
  });

  /** 超级管理：取消群绑定（删除 wx_groups 行；历史 cmd 等数据仍保留 wx_group_id） */
  r.delete('/admin/groups/:id', auth, requireRole('super'), (req, res) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id <= 0) return res.status(400).json({ error: '无效的群 id' });
    const row = db.prepare('SELECT * FROM wx_groups WHERE id = ?').get(id);
    if (!row) return res.status(404).json({ error: '群不存在' });
    db.prepare('DELETE FROM wx_groups WHERE id = ?').run(id);
    if (typeof db.persist === 'function') db.persist();
    res.json({ ok: true, wx_group_id: row.wx_group_id });
  });

  /** 自定义规则：全部为全局（wx_group_id 恒为 NULL，不按群区分） */
  r.post('/admin/rules', auth, requireRole('super', 'group_admin'), (req, res) => {
    const { name, priority, rule_type, pattern, action_json } = req.body || {};
    if (!name || !rule_type || pattern == null) return res.status(400).json({ error: '缺少必要字段' });
    if (!['keyword', 'regex', 'noop'].includes(rule_type))
      return res.status(400).json({ error: 'rule_type 无效' });
    db.prepare(
      `INSERT INTO custom_rules (wx_group_id, name, priority, rule_type, pattern, action_json)
       VALUES (?,?,?,?,?,?)`
    ).run(null, name, priority ?? 0, rule_type, String(pattern), action_json || null);
    res.json({ ok: true });
  });

  r.get('/admin/rules', auth, requireRole('super', 'group_admin'), (_req, res) => {
    const rows = db
      .prepare(
        `SELECT * FROM custom_rules
         WHERE wx_group_id IS NULL OR TRIM(COALESCE(wx_group_id,'')) = '' OR wx_group_id = '__global__'
         ORDER BY priority DESC, id DESC`
      )
      .all();
    res.json({ rules: rows });
  });

  /** 群管理：离线激活续期（一码一单群：activation_redemptions.code_fingerprint UNIQUE） */
  r.post('/admin/activate', auth, requireRole('super', 'group_admin'), (req, res) => {
    const { code, wx_group_id } = req.body || {};
    if (!code || !wx_group_id) return res.status(400).json({ error: '缺少 code 或 wx_group_id' });
    const botWxid = resolveBotWxidForLicense();
    if (!botWxid) {
      return res.status(400).json({ error: '请先登录微信后再核销激活码' });
    }
    const v = verifyLicenseCode(code, botWxid);
    if (!v.ok) return res.status(400).json({ error: '激活码无效', detail: v.reason });
    const dl = assertPayloadRedeemDeadline(v.payload);
    if (!dl.ok) {
      return res.status(400).json({ error: '该激活码已超过兑换截止时间', detail: dl.reason });
    }
    const fp = activationFingerprint(code);
    try {
      db.prepare(
        'INSERT INTO activation_redemptions (code_fingerprint, raw_payload, wx_group_id, redeemed_by_user_id) VALUES (?,?,?,?)'
      ).run(fp, JSON.stringify(v.payload), wx_group_id, req.user.uid);
    } catch {
      return res.status(400).json({ error: '激活码已使用' });
    }
    const days = Number(v.payload.days || 30);
    if (!db.prepare('SELECT id FROM wx_groups WHERE wx_group_id = ?').get(wx_group_id)) {
      upsertWxGroupBound(db, { wx_group_id });
    }
    const expiresIso = extendWxGroupExpiresAt(db, wx_group_id, days);
    if (typeof db.persist === 'function') db.persist();
    res.json({ ok: true, expires_at: expiresIso });
  });

  function summarizeInstallClaimPayload(raw) {
    try {
      const p = JSON.parse(raw || '{}');
      return {
        license_sku: p.license_sku ?? null,
        group_validity_days:
          p.group_validity_days != null ? Number(p.group_validity_days) : null,
        installation: p.installation === true,
        iat: p.iat != null ? Number(p.iat) : null,
        redeem_before: p.redeem_before != null ? Number(p.redeem_before) : null,
      };
    } catch {
      return null;
    }
  }

  function summarizeActivationPayload(raw) {
    try {
      const p = JSON.parse(raw || '{}');
      return {
        license_sku: p.license_sku ?? null,
        days: p.days != null ? Number(p.days) : null,
        iat: p.iat != null ? Number(p.iat) : null,
        redeem_before: p.redeem_before != null ? Number(p.redeem_before) : null,
      };
    } catch {
      return null;
    }
  }

  /** 运维：离线授权一览（核销摘要；完整码服务端不长期保存，仅能自行备份） */
  r.get('/admin/license/overview', auth, requireRole('super'), (_req, res) => {
    try {
      const pem =
        publicKeyPath && fs.existsSync(publicKeyPath) ? fs.readFileSync(publicKeyPath, 'utf8') : null;
      const setupClaims = db
        .prepare(
          `SELECT code_fingerprint, raw_payload, redeemed_at FROM setup_license_claims ORDER BY redeemed_at DESC`
        )
        .all();
      const groupRedemptions = db
        .prepare(
          `SELECT a.id, a.wx_group_id, a.raw_payload, a.redeemed_at, a.redeemed_by_user_id,
                  g.name AS group_name
           FROM activation_redemptions a
           LEFT JOIN wx_groups g ON g.wx_group_id = a.wx_group_id
           ORDER BY a.id DESC
           LIMIT 200`
        )
        .all();
      res.json({
        skip_product_setup: skipProductSetup(),
        public_key_configured: Boolean(pem?.trim()),
        product_setup_completed: isProductSetupCompleted(),
        install_group_bonus_available: getAppSetting(SETUP_KEYS.BONUS_AVAIL) === '1',
        install_group_bonus_days: Number(getAppSetting(SETUP_KEYS.BONUS_DAYS) || '365'),
        installation_claims: setupClaims.map((row) => ({
          ...row,
          payload_summary: summarizeInstallClaimPayload(row.raw_payload),
        })),
        group_redemptions: groupRedemptions.map((row) => ({
          ...row,
          payload_summary: summarizeActivationPayload(row.raw_payload),
        })),
      });
    } catch (e) {
      logger.error('[admin/license/overview]', e);
      res.status(500).json({ error: String(e?.message || e) });
    }
  });

  /**
   * 已首次完成产品授权后，再次核销新的「安装类」年卡：登记 claim、刷新首绑群奖励天数权益。
   * 群月卡续期请在「群管理 → 激活续期」使用 /admin/activate。
   */
  r.post('/admin/license/redeem-installation', auth, requireRole('super'), (req, res) => {
    try {
      if (skipProductSetup()) {
        return res.status(400).json({ error: '当前 SKIP_PRODUCT_SETUP=1，未启用产品授权门禁' });
      }
      if (!isProductSetupCompleted()) {
        return res.status(400).json({
          error: '尚未完成首次产品授权，请先在登录页粘贴安装码并「验证并继续」。',
        });
      }
      const code = String(req.body?.code || '').trim();
      if (!code) return res.status(400).json({ error: '请粘贴安装类授权码' });
      const botWxid = String(req.body?.wxid || resolveBotWxidForLicense() || '').trim();
      const v = verifyLicenseCode(code, botWxid);
      if (!v.ok) return res.status(400).json({ error: '授权码无效', detail: v.reason });
      const rdl = assertPayloadRedeemDeadline(v.payload);
      if (!rdl.ok) {
        return res.status(400).json({
          error: '该授权码已超过兑换截止时间',
          detail: rdl.reason,
        });
      }
      if (v.payload.installation !== true) {
        return res.status(400).json({
          error:
            '该码不是产品安装类（年卡）。微信群月卡续期请在「群管理 → 激活续期」使用群激活码。',
        });
      }
      const fp = activationFingerprint(code);
      try {
        db.prepare('INSERT INTO setup_license_claims (code_fingerprint, raw_payload) VALUES (?, ?)').run(
          fp,
          JSON.stringify(v.payload)
        );
      } catch {
        return res.status(400).json({ error: '该授权码已核销过或与历史重复' });
      }
      const days = Math.min(3660, Math.max(1, Number(v.payload.group_validity_days ?? 365) || 365));
      setAppSetting(SETUP_KEYS.BONUS_AVAIL, '1');
      setAppSetting(SETUP_KEYS.BONUS_DAYS, String(days));
      if (typeof db.persist === 'function') db.persist();
      res.json({
        ok: true,
        install_group_bonus_days: days,
        message: `新年卡已登记；若仍有「首个未填到期群的绑群权益」，将按约定约 ${days} 天写入。`,
      });
    } catch (e) {
      logger.error('[admin/license/redeem-installation]', e);
      res.status(500).json({ error: String(e?.message || e) });
    }
  });

  /** 超级管理：创建群管理员账号 */
  r.post('/admin/users', auth, requireRole('super'), (req, res) => {
    const { username, password, role } = req.body || {};
    if (!username || !password || !['group_admin', 'user'].includes(role)) {
      return res.status(400).json({ error: '参数错误' });
    }
    try {
      db.prepare('INSERT INTO users (username, password_hash, role) VALUES (?,?,?)').run(
        username,
        hashPassword(password),
        role
      );
      res.json({ ok: true });
    } catch (e) {
      res.status(400).json({ error: String(e.message) });
    }
  });

  r.get('/admin/users', auth, requireRole('super'), (_req, res) => {
    const rows = db.prepare('SELECT id, username, role, created_at FROM users ORDER BY id ASC').all();
    res.json({ items: rows });
  });

  r.patch('/admin/users/:id', auth, requireRole('super'), (req, res) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id <= 0) return res.status(400).json({ error: '无效的用户 id' });
    const target = db.prepare('SELECT * FROM users WHERE id = ?').get(id);
    if (!target) return res.status(404).json({ error: '用户不存在' });

    const body = req.body || {};
    const patchUsername = body.username !== undefined ? String(body.username).trim() : undefined;
    const patchPassword = body.password !== undefined ? String(body.password) : undefined;
    const patchRole = body.role !== undefined ? String(body.role) : undefined;

    if (patchUsername === undefined && patchPassword === undefined && patchRole === undefined) {
      return res.status(400).json({ error: '无更新内容' });
    }

    if (patchUsername !== undefined) {
      if (!patchUsername) return res.status(400).json({ error: '用户名不能为空' });
      const clash = db.prepare('SELECT id FROM users WHERE username = ? AND id != ?').get(patchUsername, id);
      if (clash) return res.status(400).json({ error: '用户名已存在' });
    }

    if (patchRole !== undefined) {
      if (!['super', 'group_admin', 'user'].includes(patchRole)) {
        return res.status(400).json({ error: '无效的角色' });
      }
      if (patchRole === 'super' && target.role !== 'super') {
        return res.status(403).json({ error: '禁止通过控制台提升为超级管理员' });
      }
      if (target.role === 'super' && patchRole !== 'super') {
        const n = Number(
          db.prepare(`SELECT COUNT(*) as c FROM users WHERE role = 'super' AND id != ?`).get(id)?.c ?? 0
        );
        if (n < 1) return res.status(400).json({ error: '至少保留一名超级管理员' });
      }
    }

    const sets = [];
    const args = [];
    if (patchUsername !== undefined) {
      sets.push('username = ?');
      args.push(patchUsername);
    }
    if (patchPassword !== undefined && patchPassword.trim() !== '') {
      sets.push('password_hash = ?');
      args.push(hashPassword(patchPassword));
    }
    if (patchRole !== undefined) {
      sets.push('role = ?');
      args.push(patchRole);
    }
    if (!sets.length) return res.status(400).json({ error: '无有效更新' });

    try {
      args.push(id);
      db.prepare(`UPDATE users SET ${sets.join(', ')} WHERE id = ?`).run(...args);
    } catch (e) {
      return res.status(400).json({ error: String(e.message) });
    }
    const row = db.prepare('SELECT id, username, role, created_at FROM users WHERE id = ?').get(id);
    res.json({ ok: true, user: row });
  });

  r.delete('/admin/users/:id', auth, requireRole('super'), (req, res) => {
    const id = Number(req.params.id);
    if (!Number.isInteger(id) || id <= 0) return res.status(400).json({ error: '无效的用户 id' });
    if (Number(req.user.uid) === id) {
      return res.status(400).json({ error: '不能删除当前登录账号' });
    }
    const target = db.prepare('SELECT role FROM users WHERE id = ?').get(id);
    if (!target) return res.status(404).json({ error: '用户不存在' });
    if (target.role === 'super') {
      return res.status(400).json({ error: '不能删除超级管理员账号' });
    }
    try {
      db.prepare('UPDATE wx_groups SET group_admin_user_id = NULL WHERE group_admin_user_id = ?').run(id);
      const rdel = db.prepare('DELETE FROM users WHERE id = ?').run(id);
      if (!rdel.changes) return res.status(404).json({ error: '用户不存在' });
      res.json({ ok: true });
    } catch (e) {
      res.status(400).json({ error: String(e.message) });
    }
  });

  r.get('/admin/audit', auth, requireRole('super'), (req, res) => {
    const rows = db.prepare('SELECT * FROM message_audit ORDER BY id DESC LIMIT 200').all();
    res.json({ items: rows });
  });

  r.get('/admin/bot/status', auth, requireRole('super', 'group_admin'), (_req, res) => {
    const inbound_enabled = getBotInboundEnabled(db);
    let started_at = null;
    if (inbound_enabled) {
      const row = db.prepare('SELECT value FROM app_settings WHERE key = ?').get(BOT_RUNTIME_STARTED_KEY);
      started_at = row?.value != null && String(row.value).trim() !== '' ? String(row.value).trim() : null;
      if (!started_at) {
        syncBotRuntimeStartedAt(db, true);
        const row2 = db.prepare('SELECT value FROM app_settings WHERE key = ?').get(BOT_RUNTIME_STARTED_KEY);
        started_at = row2?.value != null ? String(row2.value).trim() : null;
      }
    }
    res.json({
      inbound_enabled,
      started_at: started_at ? formatSqliteUtcForDisplay(started_at) : null,
    });
  });

  r.post('/admin/bot/inbound', auth, requireRole('super', 'group_admin'), (req, res) => {
    try {
      if (!isRobotLicenseValid(db) && Boolean(req.body?.enabled)) {
        return res.status(403).json({ error: '机器人主授权已过期，请先完成主程序续费' });
      }
      const enabled = Boolean(req.body?.enabled);
      const wasEnabled = getBotInboundEnabled(db);
      setBotInboundEnabled(db, enabled);
      setBotInboundUserPaused(db, !enabled);
      if (enabled && !wasEnabled) {
        syncBotRuntimeStartedAt(db, true);
        appendBotWorkLog(db, 'info', '机器人入站处理已启动', null);
      } else if (!enabled && wasEnabled) {
        syncBotRuntimeStartedAt(db, false);
        appendBotWorkLog(db, 'info', '机器人入站处理已暂停', null);
      }
      const on = getBotInboundEnabled(db);
      let started_at = null;
      if (on) {
        const row = db.prepare('SELECT value FROM app_settings WHERE key = ?').get(BOT_RUNTIME_STARTED_KEY);
        started_at = row?.value != null ? String(row.value).trim() : null;
      }
      res.json({
        ok: true,
        inbound_enabled: on,
        started_at: started_at ? formatSqliteUtcForDisplay(started_at) : null,
      });
    } catch (e) {
      logger.error('[admin/bot/inbound]', e?.message || e, e?.stack);
      res.status(500).json({ error: String(e?.message || e) });
    }
  });

  r.get('/admin/bot/work-logs', auth, requireRole('super', 'group_admin'), (req, res) => {
    const limit = Math.min(200, Math.max(1, Number(req.query.limit) || 80));
    const rows = db
      .prepare(
        `SELECT id, level, message, detail_json, created_at
         FROM bot_work_logs ORDER BY id DESC LIMIT ?`
      )
      .all(limit);
    res.json({
      logs: rows.map((r) => ({
        ...r,
        created_at: formatSqliteUtcForDisplay(r.created_at),
      })),
    });
  });

  /** 在本机运行 scripts/launch-wechat-hook.mjs（查找 Weixin + inject），仅 Windows */
  r.post('/admin/bot/wechat-inject', auth, requireRole('super', 'group_admin'), async (req, res) => {
    try {
      const result = await runWechatHookInject({
        db,
        projectRoot: PROJECT_ROOT,
        hookClient,
        logger,
      });
      if (!result.ok) {
        return res.status(500).json(result);
      }
      res.json(result);
    } catch (e) {
      logger.error('[wechat-inject]', e);
      res.status(500).json({ ok: false, error: String(e?.message || e) });
    }
  });

  r.get('/admin/hook/chatrooms', auth, requireRole('super', 'group_admin'), async (_req, res) => {
    if (!hookClient || typeof hookClient.getChatroomList !== 'function') {
      return res.status(503).json({ error: 'Hook 客户端未配置' });
    }
    const result = await hookClient.getChatroomList();
    const rawSum = hookRawPayloadSummary(result.raw);
    logger.debug?.('[hook:get_chatroom_list] raw', rawSum);
    if (!result.ok) {
      return res.status(502).json({ error: '拉取群聊列表失败', detail: result.message });
    }
    const localGroups = db.prepare('SELECT wx_group_id, name FROM wx_groups').all();
    const localNameMap = new Map(localGroups.map((g) => [g.wx_group_id, g.name || '']));
    const items = (result.items || []).map((item) => ({
      ...item,
      local_name: localNameMap.get(item.username) || '',
    }));
    for (const item of items) {
      upsertChatroomCache({
        room_id: item.username,
        nick_name: item.nick_name,
        remark: item.remark,
        small_head_url: item.small_head_url,
        big_head_url: item.big_head_url,
      });
    }
    logger.info('[hook:get_chatroom_list] ok', {
      total: items.length || result.total || 0,
      ...rawSum,
    });
    res.json({
      items,
      total: items.length || result.total || 0,
      message: result.message || '',
    });
  });

  r.get('/admin/hook/room-owner', auth, requireRole('super', 'group_admin'), async (req, res) => {
    const roomId = String(req.query.room_id || '').trim();
    if (!roomId) {
      return res.status(400).json({ error: '缺少 room_id' });
    }
    if (!hookClient || typeof hookClient.getRoomMembers !== 'function') {
      return res.status(503).json({ error: 'Hook 客户端未配置' });
    }
    const result = await hookClient.getRoomMembers(roomId);
    const rawSum = hookRawPayloadSummary(result.raw);
    logger.debug?.('[hook:get_room_members] raw', { room_id: roomId, ...rawSum });
    if (!result.ok) {
      return res.status(502).json({ error: '拉取群成员失败', detail: result.message || '' });
    }
    const ownerWxid = result.owner || '';
    const ownerMember = (result.members || []).find((m) => m.userName === ownerWxid);
    const ownerNick = ownerMember?.nickName || '';
    upsertChatroomCache({
      room_id: result.roomId || roomId,
      owner_wxid: ownerWxid,
      owner_nick: ownerNick,
      member_count: result.allMemberCount || 0,
    });
    for (const member of result.members || []) {
      upsertChatroomMember(result.roomId || roomId, member, ownerWxid);
      upsertContactProfile(member.userName, member, 'room_members_query');
    }
    logger.info('[hook:get_room_members] ok', {
      room_id: result.roomId || roomId,
      member_count: result.allMemberCount || 0,
      ...rawSum,
    });
    res.json({
      room_id: result.roomId || roomId,
      owner_wxid: ownerWxid,
      owner_nick: ownerNick,
      member_count: result.allMemberCount || 0,
    });
  });

  r.get('/admin/cache/chatrooms', auth, requireRole('super', 'group_admin'), (req, res) => {
    const rows = db.prepare('SELECT * FROM wx_chatroom_cache ORDER BY updated_at DESC, room_id ASC').all();
    res.json({ items: rows });
  });

  r.get('/admin/cache/members', auth, requireRole('super', 'group_admin'), (req, res) => {
    const roomId = String(req.query.room_id || '').trim();
    if (roomId) {
      const rows = db
        .prepare('SELECT * FROM wx_chatroom_members WHERE room_id = ? ORDER BY updated_at DESC, wxid ASC')
        .all(roomId);
      return res.json({ items: rows });
    }
    const rows = db
      .prepare('SELECT * FROM wx_chatroom_members ORDER BY updated_at DESC, room_id ASC, wxid ASC LIMIT 500')
      .all();
    res.json({ items: rows });
  });

  r.get('/admin/cache/contacts', auth, requireRole('super', 'group_admin'), (req, res) => {
    const keyword = String(req.query.keyword || '').trim();
    if (keyword) {
      const like = `%${keyword}%`;
      const rows = db
        .prepare(
          `SELECT * FROM wx_contact_profiles
           WHERE wxid LIKE ? OR nick_name LIKE ? OR display_name LIKE ?
           ORDER BY last_seen_at DESC, wxid ASC
           LIMIT 500`
        )
        .all(like, like, like);
      return res.json({ items: rows });
    }
    const rows = db
      .prepare('SELECT * FROM wx_contact_profiles ORDER BY last_seen_at DESC, wxid ASC LIMIT 500')
      .all();
    res.json({ items: rows });
  });

  r.get('/admin/cmd/collections', auth, requireRole('super', 'group_admin'), (req, res) => {
    const setName = String(req.query.set_name || '').trim();
    const setCategory = String(req.query.set_category || '').trim();
    if (setName) {
      const rows = setCategory
        ? db
            .prepare(
              `SELECT * FROM cmd_collections
               WHERE is_active = 1 AND set_name = ? AND set_category = ? AND wx_group_id IS NULL
               ORDER BY id DESC`
            )
            .all(setName, setCategory)
        : db
            .prepare(
              `SELECT * FROM cmd_collections
               WHERE is_active = 1 AND set_name = ? AND wx_group_id IS NULL
               ORDER BY id DESC`
            )
            .all(setName);
      return res.json({ items: rows });
    }
    if (setCategory) {
      const rows = db
        .prepare(
          `SELECT * FROM cmd_collections
           WHERE is_active = 1 AND set_category = ? AND wx_group_id IS NULL
           ORDER BY set_name ASC, id DESC`
        )
        .all(setCategory);
      return res.json({ items: rows });
    }
    const rows = db
      .prepare(
        `SELECT * FROM cmd_collections
         WHERE is_active = 1 AND wx_group_id IS NULL
         ORDER BY set_category ASC, set_name ASC, id DESC`
      )
      .all();
    res.json({ items: rows });
  });

  r.post('/admin/cmd/collections', auth, requireRole('super', 'group_admin'), (req, res) => {
    const { id, set_category, set_name, source_set_name, derive_indexes, items, is_active } = req.body || {};
    const rowId = id != null && id !== '' ? Math.floor(Number(id)) : null;
    if (rowId != null && (!Number.isInteger(rowId) || rowId <= 0)) {
      return res.status(400).json({ error: 'id 必须为正整数' });
    }
    const setName = String(set_name || '').trim();
    const setCategory = String(set_category || '').trim();
    if (!setName) return res.status(400).json({ error: '缺少 set_name' });
    const indexesJson = Array.isArray(derive_indexes) ? JSON.stringify(derive_indexes) : null;
    const itemsJson = Array.isArray(items) ? JSON.stringify(items) : null;
    if (Array.isArray(items) && items.length > 0) {
      const nums = items.map((x) => Number(x)).filter((x) => Number.isFinite(x));
      if (nums.length !== items.length) {
        return res.status(400).json({ error: 'items 必须为数字列表' });
      }
    }
    if (rowId != null) {
      const exists = db.prepare('SELECT id FROM cmd_collections WHERE id = ?').get(rowId);
      if (!exists?.id) return res.status(400).json({ error: '集合 id 不存在' });
      const dup = db
        .prepare('SELECT id FROM cmd_collections WHERE wx_group_id IS NULL AND set_name = ? AND id <> ?')
        .get(setName, rowId);
      if (dup?.id) return res.status(400).json({ error: '集合名已存在' });
      db.prepare(
        `UPDATE cmd_collections
         SET wx_group_id = ?,
             set_category = ?,
             set_name = ?,
             source_set_name = ?,
             derive_indexes_json = ?,
             items_json = ?,
             is_active = ?,
             updated_at = datetime('now')
         WHERE id = ?`
      ).run(
        null,
        setCategory,
        setName,
        source_set_name ? String(source_set_name).trim() : null,
        indexesJson,
        itemsJson,
        Number(is_active ?? 1) ? 1 : 0,
        rowId
      );
      return res.json({ ok: true, id: rowId });
    }
    const existing = db
      .prepare('SELECT id FROM cmd_collections WHERE wx_group_id IS NULL AND set_name = ?')
      .get(setName);
    if (existing?.id) {
      db.prepare(
        `UPDATE cmd_collections
         SET set_category = ?,
             source_set_name = ?,
             derive_indexes_json = ?,
             items_json = ?,
             is_active = ?,
             updated_at = datetime('now')
         WHERE id = ?`
      ).run(
        setCategory,
        source_set_name ? String(source_set_name).trim() : null,
        indexesJson,
        itemsJson,
        Number(is_active ?? 1) ? 1 : 0,
        existing.id
      );
    } else {
      db.prepare(
        `INSERT INTO cmd_collections
        (wx_group_id, set_category, set_name, source_set_name, derive_indexes_json, items_json, is_active, updated_at)
        VALUES (?,?,?,?,?,?,?,datetime('now'))`
      ).run(
        null,
        setCategory,
        setName,
        source_set_name ? String(source_set_name).trim() : null,
        indexesJson,
        itemsJson,
        Number(is_active ?? 1) ? 1 : 0
      );
    }
    res.json({ ok: true });
  });

  r.post('/admin/cmd/collections/reseed', auth, requireRole('super', 'group_admin'), (_req, res) => {
    try {
      reseedGlobalCollections(db);
      db.persist();
      const n = db
        .prepare(
          `SELECT COUNT(*) AS c FROM cmd_collections WHERE is_active = 1 AND wx_group_id IS NULL`
        )
        .get();
      res.json({ ok: true, count: Number(n?.c || 0) });
    } catch (e) {
      res.status(500).json({ error: String(e?.message || e) });
    }
  });

  r.delete('/admin/cmd/collections', auth, requireRole('super', 'group_admin'), (req, res) => {
    const rowId = Math.floor(Number(req.query.id || 0));
    if (!Number.isInteger(rowId) || rowId <= 0) {
      return res.status(400).json({ error: '缺少有效 id' });
    }
    const exists = db.prepare('SELECT id FROM cmd_collections WHERE id = ?').get(rowId);
    if (!exists?.id) {
      return res.status(404).json({ error: '集合不存在' });
    }
    db.prepare(
      `UPDATE cmd_collections
       SET is_active = 0,
           updated_at = datetime('now')
       WHERE id = ?`
    ).run(rowId);
    res.json({ ok: true });
  });

  r.get('/admin/cmd/formulas', auth, requireRole('super', 'group_admin'), (_req, res) => {
    const rows = db
      .prepare('SELECT * FROM cmd_formulas WHERE is_active = 1 ORDER BY updated_at DESC, id DESC')
      .all();
    res.json({ items: rows });
  });

  r.post('/admin/cmd/formulas', auth, requireRole('super'), (req, res) => {
    const { formula_name, pipeline_expr, description, is_active } = req.body || {};
    const formulaName = String(formula_name || '').trim();
    const pipelineExpr = String(pipeline_expr || '').trim();
    if (!formulaName || !pipelineExpr) {
      return res.status(400).json({ error: '缺少 formula_name 或 pipeline_expr' });
    }
    const valid = validateFormulaPipeline(pipelineExpr);
    if (!valid.ok) {
      return res.status(400).json({ error: `公式校验失败: ${valid.error}` });
    }
    db.prepare(
      `INSERT INTO cmd_formulas (formula_name, pipeline_expr, description, is_active, updated_at)
       VALUES (?,?,?,?,datetime('now'))
       ON CONFLICT(formula_name) DO UPDATE SET
         pipeline_expr=excluded.pipeline_expr,
         description=excluded.description,
         is_active=excluded.is_active,
         updated_at=datetime('now')`
    ).run(formulaName, pipelineExpr, description ? String(description) : null, Number(is_active ?? 1) ? 1 : 0);
    res.json({ ok: true });
  });

  r.get('/admin/cmd/type-vars', auth, requireRole('super', 'group_admin'), (req, res) => {
    const typeWord = String(req.query.type_word || req.query.category_word || '').trim();
    const rows = typeWord
      ? db
          .prepare(
            `SELECT * FROM cmd_type_vars
             WHERE category_word = ?
             ORDER BY var_name ASC, id DESC`
          )
          .all(typeWord)
      : db
          .prepare(
            `SELECT * FROM cmd_type_vars
             ORDER BY category_word ASC, var_name ASC, id DESC`
          )
          .all();
    res.json({
      items: rows.map((r) => ({
        ...r,
        type_word: r.category_word,
        default_value:
          String(r.var_type || 'number') === 'text'
            ? String(r.default_value_text ?? '')
            : Number(r.default_value_number ?? 0),
      })),
    });
  });

  r.post('/admin/cmd/type-vars', auth, requireRole('super', 'group_admin'), (req, res) => {
    const rowId = req.body?.id != null && req.body?.id !== '' ? Math.floor(Number(req.body?.id)) : null;
    if (rowId != null && (!Number.isInteger(rowId) || rowId <= 0)) {
      return res.status(400).json({ error: 'id 必须为正整数' });
    }
    const typeWord = String(req.body?.type_word || req.body?.category_word || '').trim();
    const varName = String(req.body?.var_name || '').trim();
    const varType = String(req.body?.var_type || 'number').trim();
    const defaultValue = req.body?.default_value;
    if (!typeWord || !varName) {
      return res.status(400).json({ error: '缺少 type_word 或 var_name' });
    }
    if (!['number', 'text'].includes(varType)) {
      return res.status(400).json({ error: 'var_type 仅支持 number/text' });
    }
    const defaultValueNumber =
      varType === 'number'
        ? (() => {
            const n = Number(defaultValue ?? 0);
            return Number.isFinite(n) ? n : null;
          })()
        : null;
    if (varType === 'number' && defaultValueNumber == null) {
      return res.status(400).json({ error: 'number 类型默认值必须为数字' });
    }
    const defaultValueText = varType === 'text' ? String(defaultValue ?? '') : null;

    if (rowId != null) {
      const ex = db.prepare('SELECT id FROM cmd_type_vars WHERE id = ?').get(rowId);
      if (!ex?.id) return res.status(400).json({ error: '变量 id 不存在' });
      const dup = db
        .prepare('SELECT id FROM cmd_type_vars WHERE category_word = ? AND var_name = ? AND id <> ?')
        .get(typeWord, varName, rowId);
      if (dup?.id) return res.status(400).json({ error: '同类型下变量名已存在' });
      db.prepare(
        `UPDATE cmd_type_vars
         SET category_word = ?,
             var_name = ?,
             var_type = ?,
             default_value_number = ?,
             default_value_text = ?,
             updated_at = datetime('now')
         WHERE id = ?`
      ).run(typeWord, varName, varType, defaultValueNumber, defaultValueText, rowId);
      return res.json({ ok: true, id: rowId });
    }
    db.prepare(
      `INSERT INTO cmd_type_vars
       (category_word, var_name, var_type, default_value_number, default_value_text, updated_at)
       VALUES (?,?,?,?,?,datetime('now'))
       ON CONFLICT(category_word, var_name) DO UPDATE SET
         var_type=excluded.var_type,
         default_value_number=excluded.default_value_number,
         default_value_text=excluded.default_value_text,
         updated_at=datetime('now')`
    ).run(typeWord, varName, varType, defaultValueNumber, defaultValueText);
    res.json({ ok: true });
  });

  r.delete('/admin/cmd/type-vars', auth, requireRole('super', 'group_admin'), (req, res) => {
    const rowId = Math.floor(Number(req.query.id || 0));
    if (!Number.isInteger(rowId) || rowId <= 0) {
      return res.status(400).json({ error: '缺少有效 id' });
    }
    const ex = db.prepare('SELECT id FROM cmd_type_vars WHERE id = ?').get(rowId);
    if (!ex?.id) return res.status(404).json({ error: '变量不存在' });
    db.prepare('DELETE FROM cmd_type_vars WHERE id = ?').run(rowId);
    res.json({ ok: true });
  });

  r.get('/admin/cmd/formula-functions', auth, requireRole('super', 'group_admin'), (_req, res) => {
    res.json({
      pipeline_note:
        '顶层步骤用 | 连接；可用英文括号 ( ) 把一段子流水线包起来，子流水线内仍用 | 分隔。支持引用：集合.<集合名>、变量.<变量名>（变量按“类型”作用域读取），例如 逐项乘(集合.牛,变量.固定费率)。下单场景建议最后加 下单(order) 步骤。',
      items: [
        {
          name: 'identity',
          usage: 'identity',
          aliases_zh: '恒等、原样、透传',
          desc: '原样透传',
          example: '恒等|算法',
        },
        {
          name: 'algo',
          usage: 'algo',
          aliases_zh: '算法',
          desc: '执行指令算法（各/加/减/乘/除）',
          example: '恒等|算法|求和',
        },
        {
          name: 'sum',
          usage: 'sum',
          aliases_zh: '求和、合计',
          desc: '求和',
          example: '恒等|算法|求和',
        },
        {
          name: 'avg',
          usage: 'avg',
          aliases_zh: '均值、平均、平均值',
          desc: '平均值',
          example: '恒等|算法|均值',
        },
        {
          name: 'count',
          usage: 'count',
          aliases_zh: '计数、数量',
          desc: '元素数量',
          example: '恒等|算法|计数',
        },
        {
          name: 'max',
          usage: 'max',
          aliases_zh: '最大、最大值',
          desc: '最大值',
          example: '恒等|算法|最大',
        },
        {
          name: 'min',
          usage: 'min',
          aliases_zh: '最小、最小值',
          desc: '最小值',
          example: '恒等|算法|最小',
        },
        {
          name: 'round',
          usage: 'round(digits)',
          aliases_zh: '四舍五入、保留小数',
          desc: '按小数位四舍五入',
          example: '恒等|算法|四舍五入(2)',
        },
        {
          name: 'floor',
          usage: 'floor',
          aliases_zh: '下取整、向下取整',
          desc: '向下取整',
          example: '恒等|算法|下取整',
        },
        {
          name: 'ceil',
          usage: 'ceil',
          aliases_zh: '上取整、向上取整',
          desc: '向上取整',
          example: '恒等|算法|上取整',
        },
        {
          name: 'clamp',
          usage: 'clamp(min,max)',
          aliases_zh: '限幅、裁剪',
          desc: '值裁剪到区间',
          example: '恒等|算法|限幅(0,999)',
        },
        {
          name: 'unique',
          usage: 'unique',
          aliases_zh: '去重',
          desc: '去重',
          example: '恒等|去重',
        },
        {
          name: 'sort_asc',
          usage: 'sort_asc',
          aliases_zh: '升序、从小到大',
          desc: '升序',
          example: '恒等|算法|升序',
        },
        {
          name: 'sort_desc',
          usage: 'sort_desc',
          aliases_zh: '降序、从大到小',
          desc: '降序',
          example: '恒等|算法|降序',
        },
        {
          name: 'each_add',
          usage: 'each_add(n|value)',
          aliases_zh: '逐项加',
          desc: '逐项加',
          example: '恒等|算法|逐项加(2)',
        },
        {
          name: 'each_sub',
          usage: 'each_sub(n|value)',
          aliases_zh: '逐项减',
          desc: '逐项减',
          example: '恒等|算法|逐项减(1)',
        },
        {
          name: 'each_mul',
          usage: 'each_mul(n|value) 或 each_mul(集合.牛,变量.固定费率)',
          aliases_zh: '逐项乘',
          desc: '逐项乘',
          example: '逐项乘(集合.牛,变量.固定费率)',
        },
        {
          name: 'each_div',
          usage: 'each_div(n|value)',
          aliases_zh: '逐项除',
          desc: '逐项除',
          example: '恒等|算法|逐项除(2)',
        },
        {
          name: 'order',
          usage: 'order',
          aliases_zh: '下单',
          desc: '显式标记为下单结果，通常放在流水线最后一步',
          example: '恒等|算法|下单',
        },
        {
          name: 'union',
          usage: 'union(牛,羊,鱼)',
          aliases_zh: '并集、合集',
          desc: '集合并集',
          example: '并集(牛,羊)|算法',
        },
        {
          name: 'intersect',
          usage: 'intersect(牛,羊)',
          aliases_zh: '交集',
          desc: '集合交集',
          example: '交集(牛,羊)|算法',
        },
        {
          name: 'diff',
          usage: 'diff(牛,羊)',
          aliases_zh: '差集',
          desc: '集合差集',
          example: '差集(牛,羊)|算法',
        },
        {
          name: 'pick',
          usage: 'pick(单项v2026,1,13,25)',
          aliases_zh: '按位取值、提取',
          desc: '按位提取集合元素',
          example: '按位取值(单项v2026,1,13,25)|算法',
        },
        {
          name: 'to_values',
          usage: 'to_values',
          aliases_zh: '转数值、转数值序列、数值序列',
          desc: '转纯数值序列',
          example: '恒等|算法|转数值',
        },
        {
          name: '生肖岁数 / zodiac_age',
          usage: '生肖岁数(生肖[,日期[,最小岁数,最大岁数]])',
          aliases_zh: '生肖岁数（与英文名 zodiac_age 等价）',
          desc: '按参考日期计算该生肖可能岁数，日期默认系统日期',
          example: '生肖岁数(牛,2026-04-21,1,90)|转数值',
        },
        {
          name: '岁数生肖 / age_zodiac',
          usage: '岁数生肖(岁数[,日期])',
          aliases_zh: '岁数生肖（与 age_zodiac 等价）',
          desc: '按参考日期计算该岁数对应生肖，日期默认系统日期',
          example: '岁数生肖(18,2026-04-21)',
        },
        {
          name: '生肖岁数范围 / zodiac_age_range',
          usage: '生肖岁数范围(生肖,最小岁数,最大岁数[,日期])',
          aliases_zh: '生肖岁数范围（与 zodiac_age_range 等价）',
          desc: '按生肖与岁数区间返回列表，日期默认系统日期',
          example: '生肖岁数范围(牛,18,60,2026-04-21)|转数值',
        },
      ],
    });
  });

  r.get('/admin/cmd/order-cycles', auth, requireRole('super', 'group_admin'), (_req, res) => {
    const rows = db
      .prepare(
        `SELECT * FROM cmd_order_cycles
         WHERE is_active = 1
         ORDER BY updated_at DESC, id DESC`
      )
      .all()
      .map((row) => {
        let dates = [];
        try {
          const parsed = JSON.parse(row.date_list_json || '[]');
          dates = Array.isArray(parsed) ? parsed : [];
        } catch {
          dates = [];
        }
        return { ...row, date_list: dates };
      });
    res.json({ items: rows });
  });

  r.post('/admin/cmd/order-cycles', auth, requireRole('super', 'group_admin'), (req, res) => {
    const {
      guide_word,
      channel_word,
      cycle_type,
      cutoff_time,
      date_list,
      weekly_days,
      is_active,
    } =
      req.body || {};
    const guideWord = String(channel_word || guide_word || '').trim();
    const cycleType = String(cycle_type || 'daily').trim();
    const startTime = '00:00';
    const cutoffTime = String(cutoff_time || '19:00').trim();
    if (!guideWord) return res.status(400).json({ error: '缺少 channel_word' });
    if (!['daily', 'weekly', 'date_list'].includes(cycleType)) {
      return res.status(400).json({ error: 'cycle_type 仅支持 daily/weekly/date_list' });
    }
    if (!/^(?:[01]?\d|2[0-3]):[0-5]\d$/.test(cutoffTime)) {
      return res.status(400).json({ error: 'cutoff_time 格式应为 HH:mm（结单时间）' });
    }
    const dateList = (Array.isArray(date_list) ? date_list : [])
      .map((x) => String(x || '').trim())
      .filter((x) => /^\d{4}-\d{2}-\d{2}$/.test(x));
    const weekly = (Array.isArray(weekly_days) ? weekly_days : [])
      .map((x) => Number(x))
      .filter((x) => Number.isInteger(x) && x >= 0 && x <= 6);
    const payloadDates =
      cycleType === 'weekly'
        ? [...new Set(weekly)].sort((a, b) => a - b)
        : cycleType === 'date_list'
          ? [...new Set(dateList)].sort()
          : [];
    db.prepare(
      `INSERT INTO cmd_order_cycles
      (guide_word, cycle_type, start_time, cutoff_time, date_list_json, is_active, updated_at)
      VALUES (?,?,?,?,?,?,datetime('now'))
      ON CONFLICT(guide_word) DO UPDATE SET
        cycle_type=excluded.cycle_type,
        start_time=excluded.start_time,
        cutoff_time=excluded.cutoff_time,
        date_list_json=excluded.date_list_json,
        is_active=excluded.is_active,
        updated_at=datetime('now')`
    ).run(
      guideWord,
      cycleType,
      startTime,
      cutoffTime,
      JSON.stringify(payloadDates),
      Number(is_active ?? 1) ? 1 : 0
    );
    res.json({ ok: true });
  });

  r.get('/admin/cmd/channels', auth, requireRole('super', 'group_admin'), (_req, res) => {
    const rows = db
      .prepare(
        `SELECT * FROM cmd_channels
         WHERE is_active = 1
         ORDER BY guide_word ASC, id DESC`
      )
      .all();
    res.json({ items: rows.map((r) => ({ ...r, channel_word: r.guide_word })) });
  });

  r.get('/admin/cmd/order-parse-settings', auth, requireRole('super', 'group_admin'), (_req, res) => {
    const setRows = listAliasConfig(db, { category: 'SET' }) || [];
    const extra = setRows
      .map((r) => String(r.alias_word || '').trim())
      .filter((w) => w && w !== '元');
    res.json({
      default_guide_word: getAppSetting('default_order_guide_word') || '',
      default_category_word: getAppSetting('default_order_category_word') || '',
      amount_unit_synonyms: extra.join(', '),
      note:
        '未写渠道+类型时自动在前面拼接默认引导。金额单位请在首页「别名中心 → 金额单位别名」维护（标准词一般为「元」）；下方字段只读展示，保存默认渠道时会把额外单位写入别名中心。',
    });
  });

  r.put('/admin/cmd/order-parse-settings', auth, requireRole('super', 'group_admin'), (req, res) => {
    try {
      const body = req.body || {};
      const dg = String(body.default_guide_word ?? '').trim();
      const dc = String(body.default_category_word ?? '').trim();
      if ((dg && !dc) || (!dg && dc)) {
        return res.status(400).json({ error: '默认渠道与分类须同时填写或同时留空' });
      }
      if (dg && dc) {
        const ok = db
          .prepare(
            `SELECT 1 FROM cmd_routes
             WHERE is_active = 1 AND guide_word = ? AND category_word = ?
               AND (wx_group_id IS NULL OR TRIM(COALESCE(wx_group_id,'')) = '' OR wx_group_id = '__global__')
             LIMIT 1`
          )
          .get(dg, dc);
        if (!ok) return res.status(400).json({ error: '默认渠道+分类须在已启用的全局路由中存在' });
      }
      setAppSetting('default_order_guide_word', dg);
      setAppSetting('default_order_category_word', dc);
      if (body.amount_unit_synonyms !== undefined) {
        importAmountUnitAliasesToAliasConfig(db, body.amount_unit_synonyms);
        setAppSetting('order_amount_unit_synonyms', '');
      }
      res.json({ ok: true });
    } catch (e) {
      return res.status(400).json({ error: String(e?.message || e) });
    }
  });

  r.post('/admin/cmd/channels', auth, requireRole('super', 'group_admin'), (req, res) => {
    try {
      const channelWord = String(req.body?.channel_word || req.body?.guide_word || '').trim();
      const oldChannelWord = String(req.body?.old_channel_word || req.body?.old_guide_word || '').trim();
      if (!channelWord) return res.status(400).json({ error: '缺少 channel_word' });

      if (!oldChannelWord || oldChannelWord === channelWord) {
        db.prepare(
          `INSERT INTO cmd_channels (guide_word, is_active, updated_at)
           VALUES (?,1,datetime('now'))
           ON CONFLICT(guide_word) DO UPDATE SET
             is_active=1,
             updated_at=datetime('now')`
        ).run(channelWord);
        return res.json({ ok: true });
      }

      const hasTargetCycle = db.prepare('SELECT id FROM cmd_order_cycles WHERE guide_word = ?').get(channelWord);
      const hasOldCycle = db.prepare('SELECT id FROM cmd_order_cycles WHERE guide_word = ?').get(oldChannelWord);
      if (hasTargetCycle?.id && hasOldCycle?.id) {
        return res.status(400).json({ error: '目标渠道已存在结单周期，无法重命名合并' });
      }
      db.prepare('UPDATE cmd_channels SET guide_word = ?, updated_at = datetime(\'now\') WHERE guide_word = ?').run(
        channelWord,
        oldChannelWord
      );
      db.prepare('UPDATE cmd_routes SET guide_word = ?, updated_at = datetime(\'now\') WHERE guide_word = ?').run(
        channelWord,
        oldChannelWord
      );
      db.prepare('UPDATE cmd_order_cycles SET guide_word = ?, updated_at = datetime(\'now\') WHERE guide_word = ?').run(
        channelWord,
        oldChannelWord
      );
      db.prepare(
        `INSERT INTO cmd_channels (guide_word, is_active, updated_at)
         VALUES (?,1,datetime('now'))
         ON CONFLICT(guide_word) DO UPDATE SET
           is_active=1,
           updated_at=datetime('now')`
      ).run(channelWord);
      return res.json({ ok: true });
    } catch (e) {
      return res.status(400).json({ error: String(e?.message || e) });
    }
  });

  r.delete('/admin/cmd/channels', auth, requireRole('super', 'group_admin'), (req, res) => {
    const channelWord = String(req.query.channel_word || req.query.guide_word || '').trim();
    if (!channelWord) return res.status(400).json({ error: '缺少 channel_word' });
    const hasChild = db.prepare('SELECT 1 FROM cmd_routes WHERE guide_word = ? LIMIT 1').get(channelWord);
    if (hasChild) {
      return res.status(400).json({ error: '该渠道下仍有类型子项，不能删除' });
    }
    db.prepare('DELETE FROM cmd_channels WHERE guide_word = ?').run(channelWord);
    db.prepare('DELETE FROM cmd_order_cycles WHERE guide_word = ?').run(channelWord);
    res.json({ ok: true });
  });

  r.get('/admin/cmd/routes', auth, requireRole('super', 'group_admin'), (_req, res) => {
    const rows = db
      .prepare(
        `SELECT * FROM cmd_routes
         WHERE is_active = 1
           AND (wx_group_id IS NULL OR TRIM(COALESCE(wx_group_id,'')) = '' OR wx_group_id = '__global__')
         ORDER BY priority DESC, id DESC`
      )
      .all();
    res.json({
      items: rows.map((r) => ({
        ...r,
        channel_word: r.guide_word,
      })),
    });
  });

  r.post('/admin/cmd/routes', auth, requireRole('super', 'group_admin'), (req, res) => {
    const { guide_word, channel_word, category_word, formula_name, reply_template, priority, is_active } =
      req.body || {};
    const guideWord = String(channel_word || guide_word || '').trim();
    const categoryWord = String(category_word || '').trim();
    if (!guideWord || !categoryWord) {
      return res.status(400).json({ error: '缺少 channel_word 或 type_word' });
    }
    const dup = db
      .prepare('SELECT id FROM cmd_routes WHERE guide_word = ? AND category_word = ?')
      .get(guideWord, categoryWord);
    if (dup?.id) {
      return res.status(400).json({ error: '该主引导词与分类组合已存在' });
    }
    try {
      db.prepare(
        `INSERT INTO cmd_routes
        (wx_group_id, route_name, guide_word, category_word, formula_name, reply_template, priority, is_active, updated_at)
        VALUES (?,?,?,?,?,?,?,?,datetime('now'))`
      ).run(
        null,
        null,
        guideWord,
        categoryWord,
        formula_name ? String(formula_name).trim() : null,
        reply_template ? String(reply_template) : null,
        Number(priority || 0),
        Number(is_active ?? 1) ? 1 : 0
      );
      db.prepare(
        `INSERT INTO cmd_channels (guide_word, is_active, updated_at)
         VALUES (?,1,datetime('now'))
         ON CONFLICT(guide_word) DO UPDATE SET
           is_active=1,
           updated_at=datetime('now')`
      ).run(guideWord);
    } catch (e) {
      if (String(e?.message || '').includes('UNIQUE')) {
        return res.status(400).json({ error: '该主引导词与分类组合已存在' });
      }
      return res.status(400).json({ error: String(e?.message || e) });
    }
    res.json({ ok: true });
  });

  r.put('/admin/cmd/routes/:id', auth, requireRole('super', 'group_admin'), (req, res) => {
    const rowId = Math.floor(Number(req.params.id || 0));
    if (!Number.isInteger(rowId) || rowId <= 0) {
      return res.status(400).json({ error: 'id 必须为正整数' });
    }
    const { guide_word, channel_word, category_word, formula_name, reply_template, priority, is_active } =
      req.body || {};
    const guideWord = String(channel_word || guide_word || '').trim();
    const categoryWord = String(category_word || '').trim();
    if (!guideWord || !categoryWord) {
      return res.status(400).json({ error: '缺少 channel_word 或 type_word' });
    }
    const ex = db.prepare('SELECT id FROM cmd_routes WHERE id = ?').get(rowId);
    if (!ex?.id) return res.status(404).json({ error: '规则不存在' });
    const dup = db
      .prepare('SELECT id FROM cmd_routes WHERE guide_word = ? AND category_word = ? AND id <> ?')
      .get(guideWord, categoryWord, rowId);
    if (dup?.id) {
      return res.status(400).json({ error: '该主引导词与分类组合已存在' });
    }
    db.prepare(
      `UPDATE cmd_routes
       SET guide_word = ?,
           category_word = ?,
           formula_name = ?,
           reply_template = ?,
           priority = ?,
           is_active = ?,
           updated_at = datetime('now')
       WHERE id = ?`
    ).run(
      guideWord,
      categoryWord,
      formula_name ? String(formula_name).trim() : null,
      reply_template ? String(reply_template) : null,
      Number(priority || 0),
      Number(is_active ?? 1) ? 1 : 0,
      rowId
    );
    db.prepare(
      `INSERT INTO cmd_channels (guide_word, is_active, updated_at)
       VALUES (?,1,datetime('now'))
       ON CONFLICT(guide_word) DO UPDATE SET
         is_active=1,
         updated_at=datetime('now')`
    ).run(guideWord);
    res.json({ ok: true, id: rowId });
  });

  r.delete('/admin/cmd/routes', auth, requireRole('super', 'group_admin'), (req, res) => {
    const rowId = Math.floor(Number(req.query.id || 0));
    if (!Number.isInteger(rowId) || rowId <= 0) {
      return res.status(400).json({ error: '缺少有效 id' });
    }
    const ex = db.prepare('SELECT id FROM cmd_routes WHERE id = ?').get(rowId);
    if (!ex?.id) return res.status(404).json({ error: '规则不存在' });
    db.prepare('DELETE FROM cmd_routes WHERE id = ?').run(rowId);
    res.json({ ok: true });
  });

  r.post('/admin/cmd/orders/clear', auth, requireRole('super'), (req, res) => {
    const {
      all,
      wx_group_id,
      group_id,
      channel_word,
      guide_word,
      category_word,
      type_word,
      sender_wxid,
      settlement_date,
    } = req.body || {};
    const isAll = Boolean(all);
    const filters = {
      wx_group_id: String(wx_group_id || group_id || '').trim(),
      guide_word: String(channel_word || guide_word || '').trim(),
      category_word: String(category_word || type_word || '').trim(),
      sender_wxid: String(sender_wxid || '').trim(),
      settlement_date: String(settlement_date || '').trim(),
    };
    const where = [];
    const params = [];
    if (filters.wx_group_id) {
      where.push('wx_group_id = ?');
      params.push(filters.wx_group_id);
    }
    if (filters.guide_word) {
      where.push('guide_word = ?');
      params.push(filters.guide_word);
    }
    if (filters.category_word) {
      where.push('category_word = ?');
      params.push(filters.category_word);
    }
    if (filters.sender_wxid) {
      where.push('sender_wxid = ?');
      params.push(filters.sender_wxid);
    }
    if (filters.settlement_date) {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(filters.settlement_date)) {
        return res.status(400).json({ error: 'settlement_date 格式应为 YYYY-MM-DD' });
      }
      where.push('settlement_date = ?');
      params.push(filters.settlement_date);
    }
    if (!isAll && where.length === 0) {
      return res.status(400).json({ error: '请至少提供一个筛选条件，或设置 all=true 全清' });
    }
    const whereSql = where.length > 0 ? ` WHERE ${where.join(' AND ')}` : '';
    const before = db.prepare(`SELECT COUNT(*) AS c FROM cmd_orders${whereSql}`).get(...params);
    const willDelete = Number(before?.c || 0);
    if (willDelete <= 0) {
      return res.json({ ok: true, deleted: 0 });
    }
    db.prepare(`DELETE FROM cmd_orders${whereSql}`).run(...params);
    res.json({
      ok: true,
      deleted: willDelete,
      scope: isAll ? 'all' : 'filtered',
      filters: {
        wx_group_id: filters.wx_group_id || undefined,
        channel_word: filters.guide_word || undefined,
        category_word: filters.category_word || undefined,
        sender_wxid: filters.sender_wxid || undefined,
        settlement_date: filters.settlement_date || undefined,
      },
    });
  });

  r.get('/admin/cmd/reports/overview', auth, requireRole('super', 'group_admin'), (req, res) => {
    const settlementMode = String(req.query.settlement_mode || 'current').trim();
    const settlementDate = String(req.query.settlement_date || '').trim();
    const channelWord = String(req.query.channel_word || '').trim();
    const categoryWord = String(req.query.category_word || '').trim();
    const wxGroupId = String(req.query.wx_group_id || '').trim();
    const topN = Math.max(1, Math.min(200, Number(req.query.top_n || 50)));

    if (!['current', 'date'].includes(settlementMode)) {
      return res.status(400).json({ error: 'settlement_mode 仅支持 current/date' });
    }
    if (settlementMode === 'date' && !/^\d{4}-\d{2}-\d{2}$/.test(settlementDate)) {
      return res.status(400).json({ error: 'settlement_date 格式应为 YYYY-MM-DD' });
    }

    const currentInnerWhere = [];
    const currentInnerParams = [];
    if (channelWord) {
      currentInnerWhere.push('guide_word = ?');
      currentInnerParams.push(channelWord);
    }
    if (categoryWord) {
      currentInnerWhere.push('category_word = ?');
      currentInnerParams.push(categoryWord);
    }
    if (wxGroupId) {
      currentInnerWhere.push('wx_group_id = ?');
      currentInnerParams.push(wxGroupId);
    }
    const currentInnerSql =
      currentInnerWhere.length > 0 ? `WHERE ${currentInnerWhere.join(' AND ')}` : '';

    const baseWhere = [];
    const baseParams = [];
    if (channelWord) {
      baseWhere.push('o.guide_word = ?');
      baseParams.push(channelWord);
    }
    if (categoryWord) {
      baseWhere.push('o.category_word = ?');
      baseParams.push(categoryWord);
    }
    if (wxGroupId) {
      baseWhere.push('o.wx_group_id = ?');
      baseParams.push(wxGroupId);
    }
    if (settlementMode === 'date') {
      baseWhere.push('o.settlement_date = ?');
      baseParams.push(settlementDate);
    }

    const sourceFrom =
      settlementMode === 'current'
        ? `
          FROM cmd_orders o
          JOIN (
            SELECT guide_word, category_word, MAX(settlement_date) AS settlement_date
            FROM cmd_orders
            ${currentInnerSql}
            GROUP BY guide_word, category_word
          ) cur
            ON o.guide_word = cur.guide_word
           AND o.category_word = cur.category_word
           AND o.settlement_date = cur.settlement_date
        `
        : `FROM cmd_orders o`;
    const whereSql = baseWhere.length > 0 ? `WHERE ${baseWhere.join(' AND ')}` : '';
    const commonSql = `${sourceFrom} ${whereSql}`;
    const commonParams =
      settlementMode === 'current' ? [...currentInnerParams, ...baseParams] : [...baseParams];

    const summary = db
      .prepare(
        `SELECT
           COUNT(*) AS detail_count,
           COUNT(DISTINCT o.sender_wxid) AS member_count,
           COUNT(DISTINCT o.item_value) AS unit_count,
           COUNT(DISTINCT o.guide_word || '|' || o.category_word) AS scope_count,
           COALESCE(SUM(o.order_amount), 0) AS total_amount
         ${commonSql}`
      )
      .get(...commonParams);

    const byChannel = db
      .prepare(
        `SELECT
           o.guide_word AS channel_word,
           COUNT(*) AS detail_count,
           COUNT(DISTINCT o.sender_wxid) AS member_count,
           COUNT(DISTINCT o.item_value) AS unit_count,
           COALESCE(SUM(o.order_amount), 0) AS total_amount
         ${commonSql}
         GROUP BY o.guide_word
         ORDER BY total_amount DESC, channel_word ASC`
      )
      .all(...commonParams);

    const byGroup = db
      .prepare(
        `SELECT
           o.wx_group_id,
           COALESCE(MAX(g.name), '') AS group_name,
           COUNT(*) AS detail_count,
           COUNT(DISTINCT o.sender_wxid) AS member_count,
           COUNT(DISTINCT o.item_value) AS unit_count,
           COALESCE(SUM(o.order_amount), 0) AS total_amount
         ${sourceFrom}
         LEFT JOIN wx_groups g
           ON g.wx_group_id = o.wx_group_id
         ${whereSql}
         GROUP BY o.wx_group_id
         ORDER BY total_amount DESC, o.wx_group_id ASC`
      )
      .all(...commonParams);

    const byCategory = db
      .prepare(
        `SELECT
           o.category_word,
           COUNT(*) AS detail_count,
           COUNT(DISTINCT o.sender_wxid) AS member_count,
           COUNT(DISTINCT o.item_value) AS unit_count,
           COALESCE(SUM(o.order_amount), 0) AS total_amount
         ${commonSql}
         GROUP BY o.category_word
         ORDER BY total_amount DESC, o.category_word ASC`
      )
      .all(...commonParams);

    const byUnit = db
      .prepare(
        `SELECT
           o.item_value,
           COUNT(*) AS detail_count,
           COUNT(DISTINCT o.sender_wxid) AS member_count,
           COALESCE(SUM(o.order_amount), 0) AS total_amount
         ${commonSql}
         GROUP BY o.item_value
         ORDER BY o.item_value ASC`
      )
      .all(...commonParams);

    const byMember = db
      .prepare(
        `SELECT
           o.sender_wxid,
           COALESCE(MAX(m.display_name), MAX(p.nick_name), MAX(m.nick_name), '') AS member_name,
           COUNT(*) AS detail_count,
           COUNT(DISTINCT o.item_value) AS unit_count,
           COALESCE(SUM(o.order_amount), 0) AS total_amount
         ${sourceFrom}
         LEFT JOIN wx_chatroom_members m
           ON m.wxid = o.sender_wxid ${wxGroupId ? "AND m.room_id = o.wx_group_id" : ''}
         LEFT JOIN wx_contact_profiles p
           ON p.wxid = o.sender_wxid
         ${whereSql}
         GROUP BY o.sender_wxid
         ORDER BY total_amount DESC, o.sender_wxid ASC
         LIMIT ${topN}`
      )
      .all(...commonParams);

    res.json({
      ok: true,
      settlement_mode: settlementMode,
      settlement_date: settlementMode === 'date' ? settlementDate : '',
      filters: {
        channel_word: channelWord || '',
        category_word: categoryWord || '',
        wx_group_id: wxGroupId || '',
      },
      summary: {
        detail_count: Number(summary?.detail_count || 0),
        member_count: Number(summary?.member_count || 0),
        unit_count: Number(summary?.unit_count || 0),
        scope_count: Number(summary?.scope_count || 0),
        total_amount: Number(summary?.total_amount || 0),
      },
      by_channel: byChannel,
      by_group: byGroup,
      by_category: byCategory,
      by_unit: byUnit,
      by_member: byMember,
    });
  });

  r.post('/admin/cmd/simulate', auth, requireRole('super', 'group_admin'), (req, res) => {
    let wxGroupId = String(req.body?.wx_group_id || '').trim();
    const original_text = String(req.body?.content ?? '');
    const content = original_text.trim();
    const after_at_strip = stripWeChatAtPrefix(content, db).trim();
    if (!content) {
      return res.status(400).json({ error: '缺少 content' });
    }
    if (!wxGroupId) {
      const row =
        req.user.role === 'super'
          ? db
              .prepare(
                `SELECT wx_group_id FROM wx_groups WHERE COALESCE(is_active, 1) = 1 ORDER BY id ASC LIMIT 1`
              )
              .get()
          : db
              .prepare(
                `SELECT wx_group_id FROM wx_groups WHERE COALESCE(is_active, 1) = 1 AND group_admin_user_id = ? ORDER BY id ASC LIMIT 1`
              )
              .get(req.user.uid);
      if (!row?.wx_group_id) {
        return res.status(400).json({
          error:
            req.user.role === 'super'
              ? '缺少 wx_group_id，且数据库中没有可用的微信群'
              : '缺少 wx_group_id，且您没有绑定可用的微信群',
        });
      }
      wxGroupId = String(row.wx_group_id).trim();
    }
    const result = executeConfiguredCommand(db, wxGroupId, content, { persist: false });
    let structural_preview = null;
    try {
      structural_preview = listOrderLineStructuralPreview(db, wxGroupId, original_text, {});
    } catch (e) {
      structural_preview = { error: e?.message || String(e), preprocessed_text: '', blocks: [] };
    }
    const debugTexts = {
      original_text,
      trimmed_text: content,
      after_at_strip: after_at_strip,
    };
    if (!result) {
      return res.json({
        ok: true,
        matched: false,
        wx_group_id: wxGroupId,
        structural_preview,
        ...debugTexts,
      });
    }
    res.json({
      ok: true,
      matched: true,
      wx_group_id: wxGroupId,
      structural_preview,
      ...debugTexts,
      blocked: Boolean(result.blocked),
      route: {
        id: result.route.id,
        name: cmdRouteDisplayLabel(result.route),
        guide_word: result.route.guide_word,
        category_word: result.route.category_word,
        formula_name: result.route.formula_name,
      },
      payload: result.payload,
      reply_text: result.replyText,
    });
  });

  r.post('/admin/cmd/formula-test', auth, requireRole('super', 'group_admin'), (req, res) => {
    const wxGroupId = String(req.body?.wx_group_id || '').trim();
    const typeWord = String(req.body?.type_word || req.body?.category_word || '').trim();
    const pipelineExpr = String(req.body?.pipeline_expr || '').trim();
    const targetText = String(req.body?.target_text || '').trim();
    const algo = String(req.body?.algo || '各').trim();
    const value = Number(req.body?.value || 0);
    if (!wxGroupId || !pipelineExpr) {
      return res.status(400).json({ error: '缺少 wx_group_id 或 pipeline_expr' });
    }
    const result = executeFormulaTest(db, {
      wxGroupId,
      typeWord,
      pipelineExpr,
      targetText,
      algo,
      value,
    });
    if (!result.ok) {
      return res.status(400).json({ error: `公式测试失败: ${result.error || 'unknown'}` });
    }
    res.json({ ok: true, ...result });
  });

  if (dataBackupService) {
    r.get('/admin/ops/backup', auth, requireRole('super'), (_req, res) => {
      try {
        res.json(dataBackupService.getStatus());
      } catch (e) {
        logger.error('[admin/ops/backup GET]', e);
        res.status(500).json({ error: String(e?.message || e) });
      }
    });
    r.post('/admin/ops/backup', auth, requireRole('super'), (_req, res) => {
      try {
        const out = dataBackupService.runManual();
        if (!out.ok) {
          return res.status(400).json(out);
        }
        res.json(out);
      } catch (e) {
        logger.error('[admin/ops/backup POST]', e);
        res.status(500).json({ error: String(e?.message || e) });
      }
    });
    r.patch('/admin/ops/backup', auth, requireRole('super'), (req, res) => {
      if (req.body == null || !Object.prototype.hasOwnProperty.call(req.body, 'backup_dir')) {
        return res.status(400).json({ error: '缺少 backup_dir（可传空字符串恢复默认目录）' });
      }
      try {
        const out = dataBackupService.setBackupDir(req.body.backup_dir);
        if (!out.ok) {
          return res.status(400).json(out);
        }
        res.json(out);
      } catch (e) {
        logger.error('[admin/ops/backup PATCH]', e);
        res.status(500).json({ error: String(e?.message || e) });
      }
    });
  }

  if (sqlitePath) {
    r.post(
      '/admin/ops/backup/import',
      auth,
      requireRole('super'),
      sqliteImportUpload.single('sqlite_file'),
      async (req, res) => {
        const buf = req.file?.buffer;
        if (!buf || buf.length === 0) {
          return res.status(400).json({
            error: '请上传有效的 SQLite .db 文件（表单字段 sqlite_file），最大约 80MB',
          });
        }
        try {
          const result = await importMainDatabaseFromBuffer(db, sqlitePath, buf, { logger });
          res.json({ ok: true, ...result });
        } catch (e) {
          logger.error('[admin/ops/backup/import]', e);
          res.status(400).json({ error: String(e?.message || e) });
        }
      }
    );
  }

  r.get('/admin/prd/license-status', auth, requireRole('super', 'group_admin'), (_req, res) => {
    applyPendingInstallRobotLicense(db);
    if (typeof db.persist === 'function') db.persist();
    const row = getRobotConfig(db);
    const prof = getPrdWechatProfile(db);
    res.json({
      robot_configured: Boolean(row),
      robot_valid: isRobotLicenseValid(db),
      integrity_ok: verifyRobotConfigRow(row),
      expire_date: row?.expire_date || null,
      wxid: prof.wxid || row?.wxid || '',
      login_wxid: prof.login_wxid || '',
      robot_wxid: prof.robot_wxid || row?.wxid || '',
    });
  });

  r.get('/admin/prd/wechat-profile', auth, requireRole('super', 'group_admin'), async (req, res) => {
    if (String(req.query.refresh || '') === '1') {
      await probeAndPersistLoginWxid(db, hookClient);
    }
    res.json(getPrdWechatProfile(db));
  });

  r.get('/admin/prd/home/nearing', auth, requireRole('super', 'group_admin'), (req, res) => {
    const days = Number(req.query.days || 7);
    res.json({ groups: listGroupsNearingExpiry(db, days) });
  });

  r.get('/admin/prd/groups', auth, requireRole('super', 'group_admin'), async (req, res) => {
    if (String(req.query.sync || '') === '1' && hookClient?.getChatroomList) {
      try {
        const { syncAllChatroomsFromHookListCache, syncAllActiveGroupDisplayNamesFromHook } =
          await import('../db/chatroom_cache_store.js');
        await syncAllChatroomsFromHookListCache(db, hookClient);
        await syncAllActiveGroupDisplayNamesFromHook(db, hookClient);
      } catch (e) {
        logger.warn('[prd/groups] sync failed:', e?.message || e);
      }
    }
    const desk = String(req.query.desk || '') === '1';
    res.json({ groups: desk ? listPrdGroupDeskRows(db) : listPrdGroups(db) });
  });

  r.post('/admin/prd/groups/:wxGroupId/bind', auth, requireRole('super', 'group_admin'), async (req, res) => {
    const gid = String(req.params.wxGroupId || '').trim();
    const code = String(req.body?.code || req.body?.last_card_cipher || '').trim();
    if (!gid || !code) return res.status(400).json({ error: '缺少群 ID 或卡密' });
    if (!isRobotLicenseValid(db)) {
      return res.status(403).json({ error: '机器人主授权已过期，请先续费主程序' });
    }
    try {
      const pem = publicKeyPath && fs.existsSync(publicKeyPath) ? fs.readFileSync(publicKeyPath, 'utf8') : null;
      const result = redeemGroupCardCipher(db, {
        wxGroupId: gid,
        code,
        publicKeyPem: pem,
        userId: req.user?.uid ?? null,
      });
      if (result.error) return res.status(400).json({ error: result.error });
      if (hookClient?.getChatroomList) {
        try {
          const { syncChatroomNickFromHookList, applyGroupOwnerOnWhitelistJoin } =
            await import('../db/chatroom_cache_store.js');
          await syncChatroomNickFromHookList(db, hookClient, gid);
          await applyGroupOwnerOnWhitelistJoin(db, hookClient, gid, getWechatLoginWxid(db));
        } catch (e) {
          logger.warn('[prd/groups/bind] hook meta sync:', e?.message || e);
        }
      }
      if (typeof db.persist === 'function') db.persist();
      let hook = { ok: false, message: 'hook unavailable' };
      if (hookClient?.sendTextMsg && result.notify_text) {
        hook = await hookClient.sendTextMsg(gid, result.notify_text);
      }
      res.json({ ok: true, ...result, hook });
    } catch (e) {
      res.status(400).json({ error: String(e?.message || e) });
    }
  });

  r.get('/admin/prd/aliases', auth, requireRole('super', 'group_admin'), (req, res) => {
    res.json({ items: listAliasConfig(db, { category: req.query.category }) });
  });

  r.post('/admin/prd/aliases', auth, requireRole('super', 'group_admin'), (req, res) => {
    try {
      const row = upsertAliasConfig(db, req.body || {});
      if (typeof db.persist === 'function') db.persist();
      invalidateParseCaches(db);
      res.json({ ok: true, ...row });
    } catch (e) {
      res.status(400).json({ error: String(e?.message || e) });
    }
  });

  r.delete('/admin/prd/aliases/:id', auth, requireRole('super', 'group_admin'), (req, res) => {
    deleteAliasConfig(db, Number(req.params.id));
    if (typeof db.persist === 'function') db.persist();
    invalidateParseCaches(db);
    res.json({ ok: true });
  });

  r.get('/admin/prd/robot-config', auth, requireRole('super'), (_req, res) => {
    const row = getRobotConfig(db);
    res.json({
      config: row || null,
      integrity_ok: verifyRobotConfigRow(row),
    });
  });

  r.post('/admin/prd/robot-config', auth, requireRole('super'), (req, res) => {
    try {
      const row = upsertRobotConfig(db, req.body || {});
      if (typeof db.persist === 'function') db.persist();
      res.json({ ok: true, ...row });
    } catch (e) {
      res.status(400).json({ error: String(e?.message || e) });
    }
  });

  r.post('/admin/prd/robot-redeem', auth, requireRole('super'), (req, res) => {
    try {
      const pem = publicKeyPath && fs.existsSync(publicKeyPath) ? fs.readFileSync(publicKeyPath, 'utf8') : null;
      const result = redeemRobotCardCipher(db, {
        code: req.body?.code || req.body?.last_card_cipher,
        publicKeyPem: pem,
        wxid: req.body?.wxid,
      });
      if (result.error) return res.status(400).json({ error: result.error });
      if (typeof db.persist === 'function') db.persist();
      res.json(result);
    } catch (e) {
      res.status(400).json({ error: String(e?.message || e) });
    }
  });

  r.post('/admin/prd/groups/:wxGroupId/redeem', auth, requireRole('super', 'group_admin'), async (req, res) => {
    const gid = String(req.params.wxGroupId || '').trim();
    const code = String(req.body?.code || '').trim();
    if (!gid || !code) return res.status(400).json({ error: '缺少群 ID 或卡密密文' });
    if (!isRobotLicenseValid(db)) {
      return res.status(403).json({ error: '机器人主授权已过期，请先续费主程序' });
    }
    if (!verifyGroupWhitelistRow(db, gid)) {
      return res.status(400).json({ error: '群授权完整性校验失败，请联系管理员' });
    }
    try {
      const pem = publicKeyPath && fs.existsSync(publicKeyPath) ? fs.readFileSync(publicKeyPath, 'utf8') : null;
      const result = redeemGroupCardCipher(db, {
        wxGroupId: gid,
        code,
        publicKeyPem: pem,
        userId: req.user?.uid ?? null,
      });
      if (result.error) return res.status(400).json({ error: result.error });
      if (typeof db.persist === 'function') db.persist();
      let hook = { ok: false, message: 'hook unavailable' };
      if (hookClient?.sendTextMsg && result.notify_text) {
        hook = await hookClient.sendTextMsg(gid, result.notify_text);
      }
      res.json({ ...result, hook });
    } catch (e) {
      res.status(400).json({ error: String(e?.message || e) });
    }
  });

  return r;
}

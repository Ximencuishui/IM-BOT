import path from 'path';
import { fileURLToPath } from 'url';
import { isWeixinProcessRunning } from '../util/weixin_process.js';
import { isRobotLicenseValid, getRobotConfig, computeGroupsDeskRevision } from '../db/prd_store.js';
import { setWechatLoginWxid } from '../db/wechat_login_store.js';
import { evaluateHookRuntime, invalidateHookRuntimeCache } from '../hook/hook_runtime.js';
import { shouldAutoWeChatInject } from '../hook/hk_kit.js';
import {
  syncAllChatroomsFromHookListCache,
  syncBoundActiveGroupsMembersFromHook,
} from '../db/chatroom_cache_store.js';
import { runWechatHookInject } from '../services/wechat_inject.js';

const __heartbeatDir = path.dirname(fileURLToPath(import.meta.url));
const DEFAULT_PROJECT_ROOT = path.join(__heartbeatDir, '..', '..');
import {
  getBotInboundEnabled,
  setBotInboundEnabled,
  syncBotRuntimeStartedAt,
  appendBotWorkLog,
} from './runtime_store.js';

function skipProductSetup() {
  return process.env.SKIP_PRODUCT_SETUP === '1';
}

export const BOT_INBOUND_USER_PAUSED_KEY = 'bot_inbound_user_paused';

const HEARTBEAT_MS = Math.max(
  5000,
  Number(process.env.BOT_TRAY_HEARTBEAT_MS || process.env.TRAY_HEARTBEAT_MS || 10_000)
);

export const BOUND_GROUP_MEMBER_SYNC_MS = Math.max(
  10_000,
  Number(process.env.BOT_GROUP_MEMBER_SYNC_MS || 60_000)
);

function isLocalTcpPortOpen(port, timeoutMs = 500) {
  return new Promise((resolve) => {
    if (process.platform !== 'win32') {
      resolve(false);
      return;
    }
    import('net')
      .then(({ default: net }) => {
        const socket = new net.Socket();
        const finish = (ok) => {
          try {
            socket.destroy();
          } catch {
            /* ignore */
          }
          resolve(ok);
        };
        socket.setTimeout(timeoutMs);
        socket.once('connect', () => finish(true));
        socket.once('timeout', () => finish(false));
        socket.once('error', () => finish(false));
        socket.connect(port, '127.0.0.1');
      })
      .catch(() => resolve(false));
  });
}

export function isBotInboundUserPaused(db) {
  const row = db.prepare('SELECT value FROM app_settings WHERE key = ?').get(BOT_INBOUND_USER_PAUSED_KEY);
  return row != null && String(row.value || '') === '1';
}

export function setBotInboundUserPaused(db, paused) {
  const v = paused ? '1' : '0';
  const row = db.prepare('SELECT key FROM app_settings WHERE key = ?').get(BOT_INBOUND_USER_PAUSED_KEY);
  if (row) {
    db.prepare(`UPDATE app_settings SET value = ?, updated_at = datetime('now') WHERE key = ?`).run(
      v,
      BOT_INBOUND_USER_PAUSED_KEY
    );
  } else {
    db.prepare(`INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, datetime('now'))`).run(
      BOT_INBOUND_USER_PAUSED_KEY,
      v
    );
  }
}

function licenseOkForInbound(db) {
  if (skipProductSetup()) return true;
  return isRobotLicenseValid(db);
}

let lastChatroomListSyncAt = 0;
let autoInjectInflight = false;
let lastAutoInjectAttemptAt = 0;
let autoInjectGiveUpUntil = 0;
let lastHookReady = false;
let memberSyncTimer = null;

const AUTO_INJECT_COOLDOWN_MS = Math.max(
  60_000,
  Number(process.env.BOT_AUTO_INJECT_COOLDOWN_MS || 120_000)
);
const AUTO_INJECT_GIVEUP_MS = Math.max(
  300_000,
  Number(process.env.BOT_AUTO_INJECT_GIVEUP_MS || 1_800_000)
);

function sleepMs(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function runBoundGroupMemberSyncIfReady(db, hookClient, logger = console) {
  if (!db || !hookClient?.getRoomMembers) return;
  if (!isWeixinProcessRunning()) return;
  const rt = await evaluateHookRuntime(db, hookClient);
  if (!rt.hook_ready) return;
  try {
    const r = await syncBoundActiveGroupsMembersFromHook(db, hookClient, { logger });
    if (r?.synced > 0) {
      logger.info?.(`[tray-heartbeat] 已同步 ${r.synced} 个绑定群的群成员/群主信息`);
      if (typeof db.persist === 'function') db.persist();
    }
  } catch (e) {
    logger.warn?.('[tray-heartbeat] 群成员同步失败:', e?.message || e);
  }
}

export function ensureInboundOnStartup(db, logger = console) {
  if (isBotInboundUserPaused(db)) {
    logger.info?.('[入站] 用户曾手动暂停，启动时保持暂停');
    return;
  }
  if (!licenseOkForInbound(db)) {
    logger.warn?.('[入站] 主授权无效，启动时不自动开启入站');
    return;
  }
  if (!getBotInboundEnabled(db)) {
    setBotInboundEnabled(db, true);
    syncBotRuntimeStartedAt(db, true);
    appendBotWorkLog(db, 'info', '服务启动：已自动开启入站处理', null);
    if (typeof db.persist === 'function') db.persist();
    logger.info?.('[入站] 启动时已自动开启入站处理');
  }
}

export async function collectTrayHeartbeat(
  db,
  { syncInbound = true, hookClient = null, projectRoot = DEFAULT_PROJECT_ROOT, logger = console } = {}
) {
  const rt = await evaluateHookRuntime(db, hookClient);

  const tcpPort = Number(process.env.TCP_PORT || 61108);
  const httpPort = Number(process.env.HTTP_PORT || 3000);
  const callbackPortRaw = Number(process.env.HOOK_CALLBACK_PORT || 0);
  const callbackPort = callbackPortRaw > 0 ? callbackPortRaw : httpPort;
  const hook_tcp_listening =
    process.platform === 'win32' ? await isLocalTcpPortOpen(tcpPort) : false;
  const hook_callback_listening =
    process.platform === 'win32' ? await isLocalTcpPortOpen(callbackPort) : false;

  const hook_ready = rt.hook_ready;
  const hook_partial =
    rt.wechat_process_running && hook_tcp_listening && !rt.hook_ready && !rt.control_ok;

  if (rt.has_live_wxid && db && rt.profile?.wxid) {
    setWechatLoginWxid(db, rt.profile.wxid, {
      nickname: rt.profile.nickname,
      avatar_url: rt.profile.avatar_url,
    });
  } else if (hook_ready && !rt.has_live_wxid && rt.has_stored_wxid && hookClient && db) {
    const { probeAndPersistLoginWxid } = await import('../db/wechat_login_store.js');
    void probeAndPersistLoginWxid(db, hookClient).catch(() => {});
  }

  const robot_valid = licenseOkForInbound(db);
  const inbound_user_paused = isBotInboundUserPaused(db);
  let inbound_sync = 'unchanged';

  if (syncInbound && !inbound_user_paused && robot_valid) {
    if (!getBotInboundEnabled(db)) {
      setBotInboundEnabled(db, true);
      syncBotRuntimeStartedAt(db, true);
      appendBotWorkLog(db, 'info', '心跳：已自动恢复入站处理', null);
      if (typeof db.persist === 'function') db.persist();
      inbound_sync = 'auto_enabled';
    }
  } else if (!robot_valid && getBotInboundEnabled(db)) {
    inbound_sync = 'license_invalid_kept';
  }

  const inbound_enabled = getBotInboundEnabled(db);

  if (hook_ready) {
    autoInjectGiveUpUntil = 0;
  }

  const now = Date.now();
  const autoInjectPaused = autoInjectGiveUpUntil > now;
  const autoInjectCooldown =
    lastAutoInjectAttemptAt > 0 && now - lastAutoInjectAttemptAt < AUTO_INJECT_COOLDOWN_MS;

  if (
    rt.needs_inject &&
    shouldAutoWeChatInject(projectRoot) &&
    !autoInjectInflight &&
    !autoInjectPaused &&
    !autoInjectCooldown
  ) {
    autoInjectInflight = true;
    lastAutoInjectAttemptAt = now;
    const injectBase = { db, projectRoot, hookClient, logger, bootstrapInject: true, quitBeforeInject: false };
    runWechatHookInject(injectBase)
      .then(async (r) => {
        if (!r?.ok) {
          logger.warn?.('[tray-heartbeat] 自动热注入失败:', r?.error || 'unknown');
          return;
        }
        logger.info?.('[tray-heartbeat] 自动热注入完成');
        invalidateHookRuntimeCache();
        await sleepMs(4000);
        const after = await evaluateHookRuntime(db, hookClient, { cacheMs: 0 });
        if (after.hook_ready) return;
        autoInjectGiveUpUntil = Date.now() + AUTO_INJECT_GIVEUP_MS;
        logger.warn?.(
          '[tray-heartbeat] 热注入后仍未就绪，请在本机微信内完成登录后点「刷新状态」（不再自动关微信）'
        );
      })
      .catch((e) => logger.warn?.('[tray-heartbeat] 自动注入异常:', e?.message || e))
      .finally(() => {
        autoInjectInflight = false;
      });
  }

  const hookJustReady = hook_ready && !lastHookReady;
  lastHookReady = hook_ready;
  if (hook_ready && hookClient?.getChatroomList) {
    const syncNow = Date.now();
    if (hookJustReady || syncNow - lastChatroomListSyncAt > 120_000) {
      lastChatroomListSyncAt = syncNow;
      syncAllChatroomsFromHookListCache(db, hookClient)
        .then((r) => {
          if (r?.ok && r.synced > 0) {
            logger.info?.(`[tray-heartbeat] 已同步 Hook 群列表 ${r.synced} 个`);
            if (typeof db.persist === 'function') db.persist();
          }
        })
        .catch((e) => logger.warn?.('[tray-heartbeat] 群列表同步失败:', e?.message || e));
    }
  }

  if (hookJustReady && hookClient?.getRoomMembers) {
    void runBoundGroupMemberSyncIfReady(db, hookClient, logger);
  }

  const groups_desk_revision = db ? computeGroupsDeskRevision(db) : '';

  return {
    service: 'sim-bot-node',
    prd_api: true,
    skip_product_setup: skipProductSetup(),
    robot_valid,
    wechat_process_running: rt.wechat_process_running,
    hook_tcp_listening,
    hook_http_ok: rt.hook_http_ok,
    hook_control_ok: rt.hook_control_ok,
    hook_has_wxid: rt.hook_has_wxid,
    hook_stored_wxid: rt.has_stored_wxid,
    hook_wechat_login_required: rt.needs_wechat_login,
    hook_callback_listening,
    hook_partial,
    hook_ready,
    hook_ready_via: rt.hook_ready_via || '',
    hook_tcp_port: tcpPort,
    hook_callback_port: callbackPort,
    inbound_enabled,
    inbound_user_paused,
    inbound_sync,
    heartbeat_ms: HEARTBEAT_MS,
    bound_group_member_sync_ms: BOUND_GROUP_MEMBER_SYNC_MS,
    groups_desk_revision,
    wechat_connected: rt.wechat_process_running,
    robot_configured: Boolean(getRobotConfig(db)),
  };
}

let heartbeatTimer = null;

export function startTrayHeartbeatLoop(db, logger = console, { hookClient = null, projectRoot = DEFAULT_PROJECT_ROOT } = {}) {
  if (heartbeatTimer) return;
  const tick = async () => {
    try {
      await collectTrayHeartbeat(db, { syncInbound: true, hookClient, projectRoot, logger });
    } catch (e) {
      logger.warn?.('[tray-heartbeat]', e?.message || e);
    }
  };
  tick();
  heartbeatTimer = setInterval(tick, HEARTBEAT_MS);
  if (hookClient?.getRoomMembers) {
    void runBoundGroupMemberSyncIfReady(db, hookClient, logger);
    memberSyncTimer = setInterval(
      () => void runBoundGroupMemberSyncIfReady(db, hookClient, logger),
      BOUND_GROUP_MEMBER_SYNC_MS
    );
  }
  logger.info?.(
    `[tray-heartbeat] 已启动（心跳 ${HEARTBEAT_MS}ms；群成员同步 ${BOUND_GROUP_MEMBER_SYNC_MS}ms）`
  );
}

export function stopTrayHeartbeatLoop() {
  if (heartbeatTimer) {
    clearInterval(heartbeatTimer);
    heartbeatTimer = null;
  }
  if (memberSyncTimer) {
    clearInterval(memberSyncTimer);
    memberSyncTimer = null;
  }
}

import { isWeixinProcessRunning } from '../util/weixin_process.js';
import { buildHookInjectConfig } from './inject_config.js';
import { shouldAutoWeChatInject } from './hk_kit.js';
import { evaluateHookRuntime, invalidateHookRuntimeCache } from './hook_runtime.js';
import { runWechatHookInject } from '../services/wechat_inject.js';

const DIGEST_KEY = 'hook_inject_config_digest';

function hookInjectDigest(projectRoot) {
  const cfg = buildHookInjectConfig(projectRoot);
  const { _meta, ...payload } = cfg;
  return JSON.stringify(payload);
}

function readStoredDigest(db) {
  const row = db.prepare('SELECT value FROM app_settings WHERE key = ?').get(DIGEST_KEY);
  return row?.value != null ? String(row.value).trim() : '';
}

function writeStoredDigest(db, digest) {
  const row = db.prepare('SELECT key FROM app_settings WHERE key = ?').get(DIGEST_KEY);
  if (row) {
    db.prepare(`UPDATE app_settings SET value = ?, updated_at = datetime('now') WHERE key = ?`).run(
      digest,
      DIGEST_KEY
    );
  } else {
    db.prepare(`INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, datetime('now'))`).run(
      DIGEST_KEY,
      digest
    );
  }
  if (typeof db.persist === 'function') db.persist();
}

/**
 * 侧车启动后：若 Hook 注入 JSON（回调 URL / 入站模式）与库中记录不一致，则关微信并冷注入一次，避免热注入沿用旧 DLL 配置（如回调仍指向 5000）。
 */
export async function ensureHookInjectConfigApplied(
  db,
  logger,
  { projectRoot, hookClient } = {}
) {
  if (!shouldAutoWeChatInject(projectRoot)) return { skipped: true, reason: 'auto_inject_disabled' };

  const digest = hookInjectDigest(projectRoot);
  const stored = readStoredDigest(db);
  const force = process.env.FORCE_HOOK_CONFIG_REINJECT === '1';
  const rt = await evaluateHookRuntime(db, hookClient, { cacheMs: 0 });
  const needWxidProbe =
    isWeixinProcessRunning() && !rt.hook_has_wxid && process.platform === 'win32';
  const needHookRecover =
    isWeixinProcessRunning() && !rt.control_ok && process.platform === 'win32';
  if (!force && stored && stored === digest && !needWxidProbe && !needHookRecover) {
    logger.info?.('[wechat-inject] Hook 注入配置未变化，跳过关微信重装');
    return { skipped: true, reason: 'digest_unchanged' };
  }
  if (needWxidProbe && stored === digest) {
    logger.info?.('[wechat-inject] 配置未变但未取得 wxid，将重新冷注入');
  }
  if (needHookRecover && stored === digest) {
    logger.info?.('[wechat-inject] 配置未变但 Hook 控制面不可达，将重新注入');
  }

  const inj = buildHookInjectConfig(projectRoot);
  const configChanged = !stored || stored !== digest;
  const coldRequired = force || configChanged;
  logger.info?.(
    `[wechat-inject] 应用 Hook 配置（${stored ? '配置已变更' : '首次'}）mode=${inj.recivemode} callback=${inj.http_callback_url}`
  );

  const prevBootstrap = process.env.WECHAT_BOOTSTRAP_INJECT;
  const prevQuit = process.env.WECHAT_QUIT_BEFORE_INJECT;
  process.env.HOOK_RECEIVE_MODE = process.env.HOOK_RECEIVE_MODE || inj.recivemode;
  process.env.HOOK_CALLBACK_URL = process.env.HOOK_CALLBACK_URL || inj.http_callback_url;

  const injectOpts = { db, projectRoot, hookClient, logger, bootstrapInject: true };

  try {
    if (!coldRequired && (needHookRecover || needWxidProbe)) {
      logger.info?.('[wechat-inject] 先热注入（不关微信）…');
      const result = await runWechatHookInject({ ...injectOpts, quitBeforeInject: false });
      invalidateHookRuntimeCache();
      const after = await evaluateHookRuntime(db, hookClient, { cacheMs: 0 });
      if (result.ok && (after.control_ok || after.hook_ready)) {
        writeStoredDigest(db, digest);
        logger.info?.('[wechat-inject] 热注入后 Hook 已就绪');
        return { ok: true, digest, mode: 'hot' };
      }
      if (!rt.has_stored_wxid) {
        logger.info?.('[wechat-inject] 热注入未恢复 Hook，将尝试冷注入（关微信后重装）…');
      }
    }

    const quit = coldRequired || (needWxidProbe && !rt.has_stored_wxid);
    const result = await runWechatHookInject({ ...injectOpts, quitBeforeInject: quit });
    invalidateHookRuntimeCache();
    if (result.ok) {
      writeStoredDigest(db, digest);
      logger.info?.(
        `[wechat-inject] Hook 配置已写入并完成注入${quit ? '（冷注入）' : ''}`
      );
      return { ok: true, digest, mode: quit ? 'cold' : 'hot' };
    }
    logger.warn?.('[wechat-inject] 配置注入失败:', result.error || 'unknown');
    return { ok: false, error: result.error };
  } finally {
    if (prevBootstrap == null) delete process.env.WECHAT_BOOTSTRAP_INJECT;
    else process.env.WECHAT_BOOTSTRAP_INJECT = prevBootstrap;
    if (prevQuit == null) delete process.env.WECHAT_QUIT_BEFORE_INJECT;
    else process.env.WECHAT_QUIT_BEFORE_INJECT = prevQuit;
  }
}

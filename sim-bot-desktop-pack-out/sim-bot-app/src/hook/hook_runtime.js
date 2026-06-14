/**
 * Hook 运行时状态（单一事实来源）
 * 供托盘心跳、启动注入、安装页与顶栏共用，避免「wxid 已正常仍报 Hook 未就绪」。
 */
import { getWechatLoginWxid } from '../db/wechat_login_store.js';
import { isWeixinProcessRunning } from '../util/weixin_process.js';
import { probeHookReadiness } from './hook_readiness.js';

let cache = { at: 0, key: '', runtime: null };

export function invalidateHookRuntimeCache() {
  cache.at = 0;
  cache.key = '';
  cache.runtime = null;
}

/**
 * @param {import('../db/database.js').Database | null} db
 * @param {ReturnType<import('./client.js').createHookClient> | null} hookClient
 * @param {{ cacheMs?: number }} [opts]
 */
export async function evaluateHookRuntime(db, hookClient, { cacheMs = 8000 } = {}) {
  const wechat_process_running = isWeixinProcessRunning();
  const stored_wxid = db ? getWechatLoginWxid(db) : '';
  const cacheKey = `${wechat_process_running}|${stored_wxid}`;
  const now = Date.now();
  if (cache.runtime && now - cache.at < cacheMs && cache.key === cacheKey) {
    return cache.runtime;
  }

  const live =
    hookClient && wechat_process_running
      ? await probeHookReadiness(hookClient)
      : {
          control_ok: false,
          operational_ok: false,
          has_wxid: false,
          wechat_login_required: false,
          profile: null,
          via: '',
          error: wechat_process_running ? 'hook_client_missing' : 'wechat_not_running',
        };

  const has_stored_wxid = Boolean(stored_wxid);
  const has_live_wxid = Boolean(live.has_wxid);

  /**
   * 就绪：微信在运行，且满足其一
   * - Hook 实测业务可用（wxid / 群列表）
   * - 库中已有 wxid 且控制面可达且非「未登录」
   */
  const hook_ready =
    wechat_process_running &&
    (live.operational_ok ||
      (has_stored_wxid && live.control_ok && !live.wechat_login_required));

  let hook_ready_via = '';
  if (live.operational_ok) hook_ready_via = live.via || 'live';
  else if (has_stored_wxid && hook_ready) hook_ready_via = 'stored_wxid';

  const hook_has_wxid = has_live_wxid || has_stored_wxid;

  const runtime = {
    wechat_process_running,
    stored_wxid,
    has_stored_wxid,
    control_ok: Boolean(live.control_ok),
    operational_ok: Boolean(live.operational_ok),
    has_live_wxid,
    wechat_login_required: Boolean(live.wechat_login_required),
    profile: live.profile,
    via: live.via || '',
    error: live.error || '',
    hook_ready,
    hook_ready_via,
    hook_http_ok: Boolean(live.control_ok),
    hook_control_ok: Boolean(live.control_ok),
    hook_has_wxid,
    /** 仅控制面/业务均不可用且库中无 wxid */
    needs_inject:
      wechat_process_running &&
      !hook_ready &&
      !has_stored_wxid &&
      !live.wechat_login_required,
    /** 微信进程在但未登录 Hook */
    needs_wechat_login: wechat_process_running && live.wechat_login_required,
  };

  cache = { at: now, key: cacheKey, runtime };
  return runtime;
}

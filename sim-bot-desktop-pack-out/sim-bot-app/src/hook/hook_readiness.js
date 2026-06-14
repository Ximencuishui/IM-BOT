/**
 * Hook 就绪探测：区分「控制面可达」「业务 API 可用」「已识别 wxid」。
 * 避免仅因 get_profile_cache 无 wxid 而误报 Hook 未就绪（群列表等已正常时）。
 */

/**
 * @param {ReturnType<import('./client.js').createHookClient>} hookClient
 * @returns {Promise<{
 *   control_ok: boolean,
 *   operational_ok: boolean,
 *   has_wxid: boolean,
 *   profile: { ok: boolean, wxid: string, nickname: string, avatar_url: string } | null,
 *   via: string,
 *   error?: string,
 * }>}
 */
export async function probeHookReadiness(hookClient) {
  const empty = {
    control_ok: false,
    operational_ok: false,
    has_wxid: false,
    profile: null,
    via: '',
  };
  if (!hookClient) return { ...empty, error: 'hook_unavailable' };

  const health =
    typeof hookClient.probeControlPlane === 'function'
      ? await hookClient.probeControlPlane()
      : await hookClient.healthProbe();
  if (!health.ok) {
    return { ...empty, error: health.error || 'health_probe_failed' };
  }

  let profile = null;
  let wxid = '';
  let via = '';
  let wechat_login_required = false;

  if (typeof hookClient.getProfileCache === 'function') {
    const prof = await hookClient.getProfileCache();
    const rawData = prof?.raw?.data;
    if (
      typeof rawData === 'string' &&
      /no\s*login/i.test(rawData)
    ) {
      wechat_login_required = true;
    }
    if (prof?.wxid) {
      wxid = String(prof.wxid).trim();
      profile = prof;
      via = 'get_profile_cache';
    }
  }

  if (!wxid && typeof hookClient.probeLoginWxid === 'function') {
    const login = await hookClient.probeLoginWxid();
    if (login.ok && login.wxid) {
      wxid = String(login.wxid).trim();
      profile = {
        ok: true,
        wxid,
        nickname: login.nickname || '',
        avatar_url: login.avatar_url || '',
      };
      via = login.apiPath || 'login_probe';
    }
  }

  let api_ok = false;
  if (!wxid && typeof hookClient.getChatroomList === 'function') {
    try {
      const rooms = await hookClient.getChatroomList();
      api_ok = Boolean(
        rooms?.ok &&
          ((Array.isArray(rooms.items) && rooms.items.length > 0) || Number(rooms.total) > 0)
      );
      if (api_ok) via = 'get_chatroom_list';
    } catch {
      /* ignore */
    }
  }

  const operational_ok = Boolean(wxid) || api_ok;

  return {
    control_ok: true,
    operational_ok,
    has_wxid: Boolean(wxid),
    wechat_login_required,
    profile: profile || (wxid ? { ok: true, wxid, nickname: '', avatar_url: '' } : null),
    via,
  };
}

/** 解析 Hook /api/get_profile_cache 响应（Apifox 个人资料缓存） */

export function strHookField(v) {
  if (v == null) return '';
  if (typeof v === 'string') return v.trim();
  if (typeof v === 'object' && typeof v.String === 'string') return v.String.trim();
  return String(v).trim();
}

/**
 * @returns {{ ok: boolean, wxid: string, nickname: string, avatar_url: string, raw: object }}
 */
export function parseProfileCacheResponse(data) {
  if (!data || typeof data !== 'object') {
    return { ok: false, wxid: '', nickname: '', avatar_url: '', raw: data };
  }
  const ui = data.userInfo && typeof data.userInfo === 'object' ? data.userInfo : {};
  const ext = data.userInfoExt && typeof data.userInfoExt === 'object' ? data.userInfoExt : {};
  const wxidCandidates = [
    strHookField(ui.userName),
    strHookField(ui.alias),
    strHookField(ui.username),
    strHookField(data.userName),
    strHookField(data.wxid),
    strHookField(data.account),
  ].filter((s) => s && !s.endsWith('@chatroom'));
  const wxid = wxidCandidates[0] || '';
  const nickname =
    strHookField(ui.nickName) || strHookField(ui.nickname) || strHookField(data.nickName);
  const avatar_url =
    strHookField(ext.smallHeadImgUrl) ||
    strHookField(ext.bigHeadImgUrl) ||
    strHookField(ui.smallHeadImgUrl) ||
    '';
  const errCode = data.errCode != null ? Number(data.errCode) : null;
  const code = data.code != null ? Number(data.code) : null;
  const explicitFail =
    (errCode != null && errCode !== 0) || (code != null && code !== 0 && code !== 1);
  const ok = Boolean(wxid) && !explicitFail;
  return { ok, wxid, nickname, avatar_url, raw: data };
}

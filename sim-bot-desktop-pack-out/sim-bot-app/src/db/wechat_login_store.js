/** 当前 PC 微信登录账号（与 robot_config 中已激活 wxid 区分） */

import { isWeixinProcessRunning } from '../util/weixin_process.js';

const KEY_LOGIN_WXID = 'wechat_login_wxid';

function strField(v) {
  if (v == null) return '';
  if (typeof v === 'string') return v.trim();
  if (typeof v === 'object' && typeof v.String === 'string') return v.String.trim();
  return String(v).trim();
}

function isPersonalWxid(wxid) {
  const s = String(wxid || '').trim();
  if (!s) return false;
  if (s.endsWith('@chatroom')) return false;
  return true;
}

/** 从 Hook TCP/HTTP 报文提取本机登录微信号 */
export function extractLoginFromHookPayload(obj) {
  if (!obj || typeof obj !== 'object') return null;

  const nested = [
    obj.user,
    obj.account_info,
    obj.login_info,
    obj.self_info,
    obj.data,
  ].filter((x) => x && typeof x === 'object');

  const candidates = [
    obj.account_wxid,
    obj.wxid,
    obj.self_wxid,
    obj.login_wxid,
    obj.userName,
    obj.username,
    obj.account,
    ...nested.flatMap((n) => [n.wxid, n.userName, n.username, n.account, n.self_wxid]),
  ];

  let wxid = '';
  for (const c of candidates) {
    const s = strField(c);
    if (isPersonalWxid(s)) {
      wxid = s;
      break;
    }
  }
  if (!wxid) return null;

  let nick = strField(obj.nickName) || strField(obj.nick_name) || strField(obj.nickname);
  let avatar = strField(obj.small_head_url) || strField(obj.smallHeadImgUrl) || strField(obj.avatar);
  for (const n of nested) {
    if (!nick) nick = strField(n.nickName) || strField(n.nick_name) || strField(n.nickname);
    if (!avatar) avatar = strField(n.small_head_url) || strField(n.smallHeadImgUrl);
  }

  return { wxid, nickname: nick, avatar_url: avatar };
}

export function getWechatLoginWxid(db) {
  const row = db.prepare('SELECT value FROM app_settings WHERE key = ?').get(KEY_LOGIN_WXID);
  return row?.value ? String(row.value).trim() : '';
}

export function setWechatLoginWxid(db, wxid, { nickname, avatar_url } = {}) {
  const id = String(wxid || '').trim();
  if (!isPersonalWxid(id)) return false;
  db.prepare(
    `INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, datetime('now'))
     ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = datetime('now')`
  ).run(KEY_LOGIN_WXID, id);
  if (nickname) {
    db.prepare(
      `INSERT INTO app_settings (key, value, updated_at) VALUES ('bot_display_nick', ?, datetime('now'))
       ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = datetime('now')`
    ).run(String(nickname));
  }
  if (avatar_url) {
    db.prepare(
      `INSERT INTO app_settings (key, value, updated_at) VALUES ('bot_display_avatar', ?, datetime('now'))
       ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = datetime('now')`
    ).run(String(avatar_url));
  }
  if (typeof db.persist === 'function') db.persist();
  return true;
}

export function syncWechatLoginFromHookPayload(db, obj) {
  const login = extractLoginFromHookPayload(obj);
  if (!login) return null;
  setWechatLoginWxid(db, login.wxid, {
    nickname: login.nickname,
    avatar_url: login.avatar_url,
  });
  return login;
}

/** 通过 Hook 控制面探测并写入 app_settings（产品授权页 / 顶栏 / 激活 wxid） */
export async function probeAndPersistLoginWxid(db, hookClient) {
  if (!hookClient) {
    return { ok: false, wxid: '', message: 'hook_unavailable' };
  }
  if (typeof hookClient.getProfileCache === 'function') {
    const prof = await hookClient.getProfileCache();
    if (prof.ok && prof.wxid) {
      setWechatLoginWxid(db, prof.wxid, {
        nickname: prof.nickname,
        avatar_url: prof.avatar_url,
      });
      return {
        ok: true,
        wxid: String(prof.wxid).trim(),
        apiPath: '/api/get_profile_cache',
        nickname: prof.nickname,
      };
    }
  }
  if (typeof hookClient.probeLoginWxid !== 'function') {
    return { ok: false, wxid: '', message: 'hook_unavailable' };
  }
  const loginProbe = await hookClient.probeLoginWxid();
  if (loginProbe.ok && loginProbe.wxid) {
    setWechatLoginWxid(db, loginProbe.wxid, {
      nickname: loginProbe.nickname,
      avatar_url: loginProbe.avatar_url,
    });
    return {
      ok: true,
      wxid: String(loginProbe.wxid).trim(),
      apiPath: loginProbe.apiPath,
      nickname: loginProbe.nickname,
    };
  }
  return {
    ok: false,
    wxid: '',
    message: String(loginProbe.message || 'hook login wxid not available'),
  };
}

/**
 * 产品授权 / 发卡用：本机微信是否已启动、是否已取得 wxid。
 * @returns {{ wxid: string, login_wxid: string, robot_wxid: string, wechat_process_running: boolean, status: 'ok'|'wechat_not_running'|'wechat_running_no_wxid', hook_probe_ok?: boolean }}
 */
export function getSetupWechatLoginStatus(db, { robotWxid = '' } = {}) {
  const loginWxid = getWechatLoginWxid(db);
  const robot = String(robotWxid || '').trim();
  const wxid = loginWxid || robot;
  const wechat_process_running = isWeixinProcessRunning();
  let status = 'ok';
  if (!wxid) {
    status = wechat_process_running ? 'wechat_running_no_wxid' : 'wechat_not_running';
  }
  return {
    wxid,
    login_wxid: loginWxid,
    robot_wxid: robot,
    wechat_process_running,
    status,
  };
}

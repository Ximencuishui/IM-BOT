/** 从 Hook JSON 中提取与 TonjClaw 类似的字段（中性，不做业务解释） */

function isChatroomWxid(wxid) {
  return /@chatroom$/i.test(String(wxid || '').trim());
}

function isPersonalWxid(wxid) {
  const s = String(wxid || '').trim();
  return Boolean(s) && !isChatroomWxid(s);
}

/** 群 ID 与 Hook 群列表 username 对齐（纯数字补 @chatroom） */
export function normalizeChatroomId(raw) {
  const s = String(raw || '').trim();
  if (!s) return '';
  if (isChatroomWxid(s)) return s;
  if (/^\d{5,}(@chatroom)?$/i.test(s)) {
    const base = s.replace(/@chatroom$/i, '');
    return `${base}@chatroom`;
  }
  return s;
}

/** 从 Hook 各字段解析群 chatroom_id（兼容 from=群 / to=群 两种布局） */
export function resolveChatroomIdFromHookPayload(obj, str) {
  if (!obj || typeof obj !== 'object') return '';
  const fromUser = str(obj.fromUserName);
  const toUser = str(obj.toUserName);
  if (isChatroomWxid(fromUser)) return fromUser;
  if (isChatroomWxid(toUser)) return toUser;

  const nestedRoom =
    obj.newChatroomData && typeof obj.newChatroomData === 'object'
      ? obj.newChatroomData
      : null;
  const candidates = [
    obj.chatRoomUserName,
    obj.chatroomUserName,
    obj.chatroom_user_name,
    obj.room_id,
    obj.roomId,
    obj.wx_group_id,
    obj.group_id,
    nestedRoom?.chatRoomUserName,
    nestedRoom?.chatroomUserName,
    obj.member_info?.chatRoomUserName,
  ];
  for (const c of candidates) {
    const s = str(c);
    if (isChatroomWxid(s)) return s;
  }
  return '';
}

export function extractWechatFields(obj) {
  if (!obj || typeof obj !== 'object') return {};

  const str = (v) => {
    if (typeof v === 'string') return v;
    if (v && typeof v === 'object' && typeof v.String === 'string') return v.String;
    return '';
  };

  const content =
    (obj.real_content != null ? String(obj.real_content) : '') ||
    str(obj.content) ||
    (obj.msg != null ? String(obj.msg) : '');
  const originalContent = str(obj.content) || (obj.msg != null ? String(obj.msg) : '');

  const fromUser = str(obj.fromUserName);
  const toUser = str(obj.toUserName);
  const reciveType = String(obj.recive_type || obj.receive_type || '');
  const groupId = normalizeChatroomId(resolveChatroomIdFromHookPayload(obj, str));
  const isGroup = Boolean(groupId) || reciveType.includes('群');

  const memberInfo = obj.member_info && typeof obj.member_info === 'object' ? obj.member_info : {};
  const sp = obj.sender_profile && typeof obj.sender_profile === 'object' ? obj.sender_profile : {};
  let senderWxid =
    str(obj.room_sender_by) ||
    str(memberInfo.userName) ||
    str(sp.userName) ||
    str(sp.friendUserName) ||
    str(obj.sender_wxid) ||
    str(obj.final_from_wxid) ||
    str(obj.from_wxid) ||
    str(obj.senderWxid) ||
    str(obj.from_user) ||
    '';

  if (groupId) {
    if (isPersonalWxid(fromUser) && (!senderWxid || senderWxid === groupId)) senderWxid = fromUser;
    if (!senderWxid || isChatroomWxid(senderWxid)) {
      const oc = str(obj.content) || (obj.msg != null ? String(obj.msg) : '');
      const gm = oc.match(/^([^:\n：]+)[:：]\s*\n/);
      const guessed = gm?.[1]?.trim();
      if (isPersonalWxid(guessed)) senderWxid = guessed;
    }
  } else if (!isGroup && isPersonalWxid(fromUser)) {
    senderWxid = senderWxid || fromUser;
  }

  const senderNick =
    str(memberInfo.displayName) ||
    str(memberInfo.nickName) ||
    str(sp.nickName) ||
    str(obj.sender_nick) ||
    str(obj.nickname) ||
    str(obj.final_from_name) ||
    str(obj.sender_name) ||
    (!groupId ? fromUser : '');

  return {
    groupId,
    senderWxid: senderWxid || '',
    senderNick: senderNick || '',
    content: String(content).trim(),
    originalContent: String(originalContent || '').trim(),
    eventType: obj.event_type,
    msgType: obj.msgType,
    raw: obj,
  };
}

function strFieldLoose(v) {
  if (v == null) return '';
  if (typeof v === 'string') return v;
  if (typeof v === 'object' && typeof v.String === 'string') return v.String;
  return String(v);
}

/**
 * 从撤回事件报文中取出「被撤回消息」的 msgId / newMsgId（用于扣减订单）。
 * 不使用当前帧顶层的 newMsgId/msgId（多为系统通知自身）。
 */
export function extractRevokedWxMessageIds(obj) {
  const out = { msgId: '', newMsgId: '' };
  if (!obj || typeof obj !== 'object') return out;
  const pick = (v) => {
    const s = String(v ?? '').trim();
    if (!s) return '';
    return s;
  };
  const flatKeysMsg = [
    'revoked_msg_id',
    'revokedMsgId',
    'revoke_msg_id',
    'ref_msg_id',
    'oldMsgId',
    'old_msg_id',
    'withdraw_msg_id',
    'withdrawMsgId',
  ];
  const flatKeysNew = [
    'revoked_new_msg_id',
    'revokedNewMsgId',
    'revoke_new_msg_id',
    'ref_new_msg_id',
    'oldNewMsgId',
    'old_new_msg_id',
    'withdraw_new_msg_id',
    'withdrawNewMsgId',
  ];
  for (const k of flatKeysMsg) {
    const v = pick(obj[k]);
    if (v) {
      out.msgId = v;
      break;
    }
  }
  for (const k of flatKeysNew) {
    const v = pick(obj[k]);
    if (v) {
      out.newMsgId = v;
      break;
    }
  }
  const xmlSources = [
    strFieldLoose(obj.content),
    strFieldLoose(obj.real_content),
    strFieldLoose(obj.replacemsg),
    strFieldLoose(obj.msg_content),
    strFieldLoose(obj.xml),
  ].filter(Boolean);
  for (const text of xmlSources) {
    const t = String(text);
    if (!out.newMsgId) {
      const m =
        t.match(/<newmsgid[^>]*>\s*([^<\s]+)\s*</i) ||
        t.match(/newmsgid["']?\s*[:=]\s*["']?(\d+)/i) ||
        t.match(/"newmsgid"\s*:\s*"?(\d+)"?/i);
      if (m) out.newMsgId = pick(m[1]);
    }
    if (!out.msgId) {
      const m2 = t.match(/<msgid[^>]*>\s*([^<\s]+)\s*</i) || t.match(/"msgid"\s*:\s*"?(\d+)"?/i);
      if (m2) out.msgId = pick(m2[1]);
    }
  }
  return out;
}

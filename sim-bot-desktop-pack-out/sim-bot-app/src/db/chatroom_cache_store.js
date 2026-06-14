/** 群成员/群主缓存（与 Hook get_room_members 同步，供管理台展示等使用） */

function normWxid(w) {
  return String(w || '').trim().toLowerCase();
}

/** Hook 成员 status：群主 / 群管理员（写入 is_owner 供管理台展示） */
function memberIsChatroomManager(member, ownerWxid) {
  const wxid = member?.wxid || member?.userName || '';
  if (!wxid) return false;
  if (ownerWxid && normWxid(wxid) === normWxid(ownerWxid)) return true;
  const st = Number(member?.status ?? member?.Status ?? 0);
  if (st === 2050 || st === 2049 || st === 2048) return true;
  if ((st & 2048) !== 0 || (st & 2050) !== 0) return true;
  return Number(member?.is_owner ?? member?.isOwner ?? 0) === 1;
}

/** 非有效群昵称（chatroom_id、破折号占位等） */
export function isPlaceholderGroupDisplayName(roomId, name) {
  const rid = String(roomId || '').trim();
  const n = String(name || '').trim();
  if (!n) return true;
  if (n === rid) return true;
  if (n === '—' || n === '-' || n === '— —') return true;
  if (/@chatroom$/i.test(n)) return true;
  if (/^\d{6,}@chatroom$/i.test(n)) return true;
  return false;
}

/** 展示用群名：Hook 群列表昵称优先，其次管理台 admin_label / 已填 name */
export function resolveChatroomDisplayName(db, roomId) {
  const rid = String(roomId || '').trim();
  if (!rid) return '';
  const g = db
    .prepare(`SELECT name, admin_label FROM wx_groups WHERE wx_group_id = ? LIMIT 1`)
    .get(rid);
  const c = db
    .prepare(`SELECT nick_name, remark FROM wx_chatroom_cache WHERE room_id = ? LIMIT 1`)
    .get(rid);
  let wlName = '';
  try {
    const wl = db.prepare(`SELECT group_name FROM group_whitelist WHERE group_id = ? LIMIT 1`).get(rid);
    wlName = String(wl?.group_name || '').trim();
  } catch {
    /* empty */
  }
  const candidates = [
    String(c?.nick_name || '').trim(),
    String(c?.remark || '').trim(),
    String(g?.admin_label || '').trim(),
    String(g?.name || '').trim(),
    wlName,
  ];
  for (const n of candidates) {
    if (n && !isPlaceholderGroupDisplayName(rid, n)) return n;
  }
  return '';
}

export function upsertChatroomCache(db, room) {
  if (!room?.room_id) return;
  db.prepare(
    `INSERT INTO wx_chatroom_cache
    (room_id, nick_name, remark, small_head_url, big_head_url, owner_wxid, owner_nick, member_count, updated_at)
    VALUES (?,?,?,?,?,?,?,?,datetime('now'))
    ON CONFLICT(room_id) DO UPDATE SET
      nick_name=CASE WHEN TRIM(COALESCE(excluded.nick_name,'')) <> '' THEN excluded.nick_name ELSE wx_chatroom_cache.nick_name END,
      remark=CASE WHEN TRIM(COALESCE(excluded.remark,'')) <> '' THEN excluded.remark ELSE wx_chatroom_cache.remark END,
      small_head_url=COALESCE(NULLIF(excluded.small_head_url,''), wx_chatroom_cache.small_head_url),
      big_head_url=COALESCE(NULLIF(excluded.big_head_url,''), wx_chatroom_cache.big_head_url),
      owner_wxid=COALESCE(NULLIF(excluded.owner_wxid,''), wx_chatroom_cache.owner_wxid),
      owner_nick=COALESCE(NULLIF(excluded.owner_nick,''), wx_chatroom_cache.owner_nick),
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

export function upsertChatroomMember(db, roomId, member, ownerWxid) {
  const wxid = member?.wxid || member?.userName || '';
  if (!roomId || !wxid) return;
  const isOwner = memberIsChatroomManager(member, ownerWxid) ? 1 : 0;
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
    isOwner
  );
}

/**
 * 从 Hook 拉取群成员并写入 wx_chatroom_cache / wx_chatroom_members。
 * @returns {Promise<boolean>} 是否成功写入群主 wxid
 */
export async function syncChatroomMembersFromHook(db, hookClient, roomId) {
  const rid = String(roomId || '').trim();
  if (!rid || !hookClient || typeof hookClient.getRoomMembers !== 'function') return false;
  const result = await hookClient.getRoomMembers(rid);
  if (!result?.ok) return false;
  const ownerWxid = String(result.owner || '').trim();
  const raw = result.raw && typeof result.raw === 'object' ? result.raw : {};
  const roomNick = String(
    raw.nickName ||
      raw.nick_name ||
      raw.chatRoomName ||
      raw.chatroomName ||
      raw.roomName ||
      ''
  ).trim();
  const roomKey = String(result.roomId || rid).trim();
  upsertChatroomCache(db, {
    room_id: roomKey,
    nick_name: roomNick,
    owner_wxid: ownerWxid,
    owner_nick: '',
    member_count: result.allMemberCount || 0,
  });
  db.prepare(`UPDATE wx_chatroom_members SET is_owner = 0 WHERE room_id = ?`).run(roomKey);
  for (const member of result.members || []) {
    upsertChatroomMember(db, roomKey, member, ownerWxid);
  }
  if (ownerWxid) persistHookOwnerToStores(db, roomKey, ownerWxid);
  if (!roomNick && hookClient.getChatroomList) {
    await syncChatroomNickFromHookList(db, hookClient, rid);
  } else {
    syncGroupDisplayMetaFromCache(db, rid);
  }
  if (typeof db.persist === 'function') db.persist();
  return Boolean(ownerWxid);
}

export function getCachedChatroomOwnerWxid(db, roomId) {
  const row = db
    .prepare('SELECT owner_wxid FROM wx_chatroom_cache WHERE room_id = ? LIMIT 1')
    .get(String(roomId || '').trim());
  return String(row?.owner_wxid || '').trim();
}

/** 群展示名与人数（写入卡密/白名单用） */
export function getChatroomDisplayMeta(db, roomId) {
  const rid = String(roomId || '').trim();
  if (!rid) return { name: '', member_count: 0 };
  const c = db
    .prepare(`SELECT member_count FROM wx_chatroom_cache WHERE room_id = ? LIMIT 1`)
    .get(rid);
  const cnt = db.prepare(`SELECT COUNT(*) AS n FROM wx_chatroom_members WHERE room_id = ?`).get(rid);
  const name = resolveChatroomDisplayName(db, rid);
  const member_count = Math.max(Number(c?.member_count || 0), Number(cnt?.n || 0));
  return { name, member_count };
}

/** 将解析后的群名、人数写入 wx_groups / group_whitelist（覆盖占位名） */
export function syncGroupDisplayMetaFromCache(db, roomId) {
  const rid = String(roomId || '').trim();
  if (!rid) return { name: '', member_count: 0 };
  const name = resolveChatroomDisplayName(db, rid);
  const c = db
    .prepare(`SELECT member_count FROM wx_chatroom_cache WHERE room_id = ? LIMIT 1`)
    .get(rid);
  const cnt = db.prepare(`SELECT COUNT(*) AS n FROM wx_chatroom_members WHERE room_id = ?`).get(rid);
  const member_count = Math.max(Number(c?.member_count || 0), Number(cnt?.n || 0));
  if (name) {
    const row = db.prepare(`SELECT name FROM wx_groups WHERE wx_group_id = ?`).get(rid);
    if (!row || isPlaceholderGroupDisplayName(rid, row.name)) {
      db.prepare(`UPDATE wx_groups SET name = ? WHERE wx_group_id = ?`).run(name, rid);
    }
  }
  try {
    const wl = db.prepare(`SELECT group_id, group_name FROM group_whitelist WHERE group_id = ?`).get(rid);
    if (wl) {
      const wlName = String(wl.group_name || '').trim();
      const nextName =
        name && isPlaceholderGroupDisplayName(rid, wlName) ? name : wlName || name || '';
      db.prepare(
        `UPDATE group_whitelist
         SET group_name = CASE WHEN TRIM(?) <> '' THEN ? ELSE group_name END,
             member_count = CASE WHEN ? > 0 THEN ? ELSE member_count END
         WHERE group_id = ?`
      ).run(nextName, nextName, member_count, member_count, rid);
    }
  } catch {
    /* group_whitelist 未迁移 */
  }
  return { name, member_count };
}

/** 从 Hook 群列表拉取单个群的 nick_name/remark 写入缓存 */
export async function syncChatroomNickFromHookList(db, hookClient, roomId) {
  const rid = String(roomId || '').trim();
  if (!rid || !hookClient || typeof hookClient.getChatroomList !== 'function') return false;
  const result = await hookClient.getChatroomList();
  if (!result?.ok) return false;
  const item = (result.items || []).find((x) => String(x.username || '').trim() === rid);
  if (!item) return false;
  const nick = String(item.nick_name || item.nickName || '').trim();
  const remark = String(item.remark || '').trim();
  if (!nick && !remark) return false;
  upsertChatroomCache(db, {
    room_id: rid,
    nick_name: nick,
    remark: remark,
    small_head_url: item.small_head_url || '',
    big_head_url: item.big_head_url || '',
  });
  syncGroupDisplayMetaFromCache(db, rid);
  if (typeof db.persist === 'function') db.persist();
  return true;
}

/** Hook 就绪时：将全部群聊写入 wx_chatroom_cache（群管理列表数据源） */
export async function syncAllChatroomsFromHookListCache(db, hookClient) {
  if (!hookClient || typeof hookClient.getChatroomList !== 'function') {
    return { ok: false, synced: 0, message: 'hook unavailable' };
  }
  const result = await hookClient.getChatroomList();
  if (!result?.ok) {
    return { ok: false, synced: 0, message: result.message || 'get_chatroom_list failed' };
  }
  let synced = 0;
  for (const item of result.items || []) {
    const rid = String(item.username || '').trim();
    if (!rid || !rid.endsWith('@chatroom')) continue;
    upsertChatroomCache(db, {
      room_id: rid,
      nick_name: item.nick_name || item.nickName || '',
      remark: item.remark || '',
      small_head_url: item.small_head_url || '',
      big_head_url: item.big_head_url || '',
    });
    synced += 1;
  }
  if (synced > 0 && typeof db.persist === 'function') db.persist();
  return { ok: true, synced, total: Number(result.total || synced) };
}

/** 为所有已绑定群从 Hook 群列表刷新昵称（管理台「刷新」时调用） */
export async function syncAllActiveGroupDisplayNamesFromHook(db, hookClient) {
  if (!hookClient || typeof hookClient.getChatroomList !== 'function') return { ok: false, updated: 0 };
  const result = await hookClient.getChatroomList();
  if (!result?.ok) return { ok: false, updated: 0, message: result.message || '' };
  const byId = new Map(
    (result.items || []).map((x) => [String(x.username || '').trim(), x]).filter(([k]) => k)
  );
  const groups = db
    .prepare(`SELECT wx_group_id FROM wx_groups WHERE is_active = 1`)
    .all()
    .map((r) => String(r.wx_group_id || '').trim())
    .filter(Boolean);
  let updated = 0;
  for (const gid of groups) {
    const item = byId.get(gid);
    if (!item) continue;
    const nick = String(item.nick_name || '').trim();
    const remark = String(item.remark || '').trim();
    if (!nick && !remark) continue;
    upsertChatroomCache(db, {
      room_id: gid,
      nick_name: nick,
      remark: remark,
      small_head_url: item.small_head_url || '',
      big_head_url: item.big_head_url || '',
    });
    syncGroupDisplayMetaFromCache(db, gid);
    updated += 1;
  }
  if (typeof db.persist === 'function') db.persist();
  return { ok: true, updated, total: groups.length };
}

/** 本地是否尚无可用群主信息（Hook 同步前） */
export function isGroupOwnerInfoEmpty(db, wxGroupId) {
  const room = String(wxGroupId || '').trim();
  if (!room) return false;
  if (getCachedChatroomOwnerWxid(db, room)) return false;
  const g = db.prepare('SELECT manual_owner FROM wx_groups WHERE wx_group_id = ?').get(room);
  if (String(g?.manual_owner || '').trim()) return false;
  try {
    const wl = db.prepare('SELECT owner_wxid FROM group_whitelist WHERE group_id = ?').get(room);
    if (String(wl?.owner_wxid || '').trim()) return false;
  } catch {
    /* 表未迁移 */
  }
  const anyOwner = db
    .prepare('SELECT 1 FROM wx_chatroom_members WHERE room_id = ? AND is_owner = 1 LIMIT 1')
    .get(room);
  return !anyOwner;
}

/** Hook 同步后把群主写入 wx_groups / group_whitelist（仅填空，不覆盖已有备注群主） */
export function persistHookOwnerToStores(db, roomId, ownerWxid) {
  const room = String(roomId || '').trim();
  const owner = String(ownerWxid || '').trim();
  if (!room || !owner) return;
  setChatroomOwnerWxid(db, room, owner);
  upsertChatroomMember(db, room, { userName: owner }, owner);
  const g = db.prepare('SELECT manual_owner, name FROM wx_groups WHERE wx_group_id = ?').get(room);
  if (g && !String(g.manual_owner || '').trim()) {
    db.prepare(`UPDATE wx_groups SET manual_owner = ? WHERE wx_group_id = ?`).run(owner, room);
  }
  const cache = db.prepare(`SELECT nick_name FROM wx_chatroom_cache WHERE room_id = ?`).get(room);
  try {
    const wl = db.prepare(`SELECT group_id, owner_wxid, group_name FROM group_whitelist WHERE group_id = ?`).get(
      room
    );
    if (wl && !String(wl.owner_wxid || '').trim()) {
      const groupName = String(g?.name || cache?.nick_name || wl.group_name || '').trim();
      db.prepare(
        `UPDATE group_whitelist
         SET owner_wxid = ?, group_name = CASE WHEN TRIM(COALESCE(group_name,'')) = '' THEN ? ELSE group_name END
         WHERE group_id = ?`
      ).run(owner, groupName, room);
    }
  } catch {
    /* 表未迁移 */
  }
}

/** 写入/覆盖群缓存中的群主 wxid（加入白名单等场景需强制更新） */
export function setChatroomOwnerWxid(db, roomId, ownerWxid) {
  const rid = String(roomId || '').trim();
  const owner = String(ownerWxid || '').trim();
  if (!rid || !owner) return;
  const ex = db.prepare('SELECT room_id FROM wx_chatroom_cache WHERE room_id = ?').get(rid);
  if (ex) {
    db.prepare(
      `UPDATE wx_chatroom_cache SET owner_wxid = ?, updated_at = datetime('now') WHERE room_id = ?`
    ).run(owner, rid);
  } else {
    upsertChatroomCache(db, { room_id: rid, owner_wxid: owner, member_count: 0 });
  }
}

/**
 * 加入白名单核销成功：拉 Hook 群主、写入 manual_owner / 成员表 / group_whitelist。
 * @param {string} senderWxid 提交卡密的成员（Hook 无群主时作为备注群主）
 */
export async function applyGroupOwnerOnWhitelistJoin(db, hookClient, roomId, senderWxid) {
  const room = String(roomId || '').trim();
  const sender = String(senderWxid || '').trim();
  if (!room) return { owner_wxid: '', manual_owner: '' };

  if (hookClient) {
    try {
      await syncChatroomMembersFromHook(db, hookClient, room);
    } catch {
      /* Hook 不可用时仍用提交者 */
    }
  }

  let hookOwner = getCachedChatroomOwnerWxid(db, room);
  if (!hookOwner && sender) {
    setChatroomOwnerWxid(db, room, sender);
    hookOwner = sender;
    upsertChatroomMember(db, room, { userName: sender }, sender);
  } else if (sender) {
    upsertChatroomMember(db, room, { userName: sender }, hookOwner);
  }

  const manualOwner = hookOwner || sender;
  if (manualOwner) {
    const ex = db.prepare('SELECT wx_group_id FROM wx_groups WHERE wx_group_id = ?').get(room);
    if (ex) {
      db.prepare(`UPDATE wx_groups SET manual_owner = ?, is_active = 1 WHERE wx_group_id = ?`).run(
        manualOwner,
        room
      );
    }
  }

  syncGroupDisplayMetaFromCache(db, room);
  const g = db.prepare(`SELECT name, manual_owner FROM wx_groups WHERE wx_group_id = ?`).get(room);
  const ownerForWl = hookOwner || g?.manual_owner || sender || '';
  const groupName = String(g?.name || '').trim();
  try {
    const wl = db.prepare(`SELECT group_id FROM group_whitelist WHERE group_id = ?`).get(room);
    if (wl) {
      db.prepare(
        `UPDATE group_whitelist
         SET owner_wxid = ?, group_name = CASE WHEN TRIM(COALESCE(group_name,'')) = '' THEN ? ELSE group_name END
         WHERE group_id = ?`
      ).run(ownerForWl, groupName, room);
    }
  } catch {
    /* group_whitelist 未迁移 */
  }

  return { owner_wxid: hookOwner, manual_owner: manualOwner };
}

const boundGroupMemberSyncInflight = new Set();

/**
 * 已绑定活跃群：从 Hook 同步成员与群主信息（由 tray 心跳每 1 分钟调度一次）。
 */
export async function syncBoundActiveGroupsMembersFromHook(db, hookClient, { logger = console } = {}) {
  if (!db || !hookClient || typeof hookClient.getRoomMembers !== 'function') {
    return { ok: false, synced: 0, skipped: 0 };
  }
  let rows = [];
  try {
    rows = db
      .prepare(`SELECT wx_group_id FROM wx_groups WHERE is_active = 1 ORDER BY wx_group_id ASC`)
      .all();
  } catch {
    return { ok: false, synced: 0, skipped: 0 };
  }
  let synced = 0;
  let skipped = 0;
  for (const row of rows) {
    const room = String(row.wx_group_id || '').trim();
    if (!room || !room.includes('@chatroom')) {
      skipped += 1;
      continue;
    }
    if (boundGroupMemberSyncInflight.has(room)) {
      skipped += 1;
      continue;
    }
    boundGroupMemberSyncInflight.add(room);
    try {
      const ok = await syncChatroomMembersFromHook(db, hookClient, room);
      if (ok) synced += 1;
      else skipped += 1;
    } catch (e) {
      skipped += 1;
      logger.warn?.('[chatroom-sync] 群成员同步失败:', room, e?.message || e);
    } finally {
      boundGroupMemberSyncInflight.delete(room);
    }
  }
  if (synced > 0 && typeof db.persist === 'function') db.persist();
  return { ok: true, synced, skipped, total: rows.length };
}

export { normWxid };

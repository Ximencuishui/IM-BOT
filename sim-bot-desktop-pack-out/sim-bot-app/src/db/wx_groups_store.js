/**
 * 微信群绑定（wx_groups）落库：幂等写入，避免重复导入/重启后需重新绑定。
 */
import { normalizeChatroomId } from '../tcp/extract.js';

function trimOpt(x) {
  if (x == null) return null;
  const s = String(x).trim();
  return s === '' ? null : s;
}

/**
 * 创建或更新群绑定记录（不删除已有到期日，除非显式传入 expires_at）。
 * @returns {{ created: boolean, wx_group_id: string }}
 */
export function upsertWxGroupBound(db, fields) {
  const gid = String(fields?.wx_group_id || '').trim();
  if (!gid) throw new Error('缺少 wx_group_id');

  const ex = db.prepare('SELECT * FROM wx_groups WHERE wx_group_id = ?').get(gid);
  const name = fields.name !== undefined ? trimOpt(fields.name) : undefined;
  const manual_owner = fields.manual_owner !== undefined ? trimOpt(fields.manual_owner) : undefined;
  const expires_at = fields.expires_at !== undefined ? fields.expires_at : undefined;
  const group_admin_user_id =
    fields.group_admin_user_id !== undefined ? fields.group_admin_user_id : undefined;
  const strict_play_routes = fields.strict_play_routes;

  if (!ex) {
    const sr = strict_play_routes != null ? (strict_play_routes ? 1 : 0) : 0;
    db.prepare(
      `INSERT INTO wx_groups
       (wx_group_id, name, group_admin_user_id, expires_at, manual_owner, is_active, strict_play_routes)
       VALUES (?,?,?,?,?,1,?)`
    ).run(
      gid,
      name ?? null,
      group_admin_user_id ?? null,
      expires_at ?? null,
      manual_owner ?? null,
      sr
    );
    return { created: true, wx_group_id: gid };
  }

  const nextName = name !== undefined ? name : ex.name;
  const nextOwner = manual_owner !== undefined ? manual_owner : ex.manual_owner;
  const nextExp = expires_at !== undefined ? expires_at : ex.expires_at;
  const nextGa = group_admin_user_id !== undefined ? group_admin_user_id : ex.group_admin_user_id;
  let nextStrict = Number(ex.strict_play_routes ?? 0);
  if (strict_play_routes !== undefined) nextStrict = strict_play_routes ? 1 : 0;

  db.prepare(
    `UPDATE wx_groups
     SET name = ?, group_admin_user_id = ?, expires_at = ?, manual_owner = ?,
         is_active = 1, strict_play_routes = ?
     WHERE wx_group_id = ?`
  ).run(nextName, nextGa, nextExp, nextOwner, nextStrict, gid);

  return { created: false, wx_group_id: gid };
}

/** 群是否已在白名单（wx_groups 且 is_active=1） */
export function isActiveWhitelistedGroup(db, wxGroupId) {
  const gid = normalizeChatroomId(wxGroupId);
  if (!gid) return false;
  return Boolean(
    db.prepare('SELECT 1 FROM wx_groups WHERE wx_group_id = ? AND is_active = 1 LIMIT 1').get(gid)
  );
}

/** 在现有到期日基础上续期（已过期则从今日起算） */
export function extendWxGroupExpiresAt(db, wxGroupId, addDays) {
  const gid = String(wxGroupId || '').trim();
  const days = Math.min(3660, Math.max(1, Number(addDays) || 30));
  const row = db.prepare('SELECT expires_at FROM wx_groups WHERE wx_group_id = ?').get(gid);
  const base = row?.expires_at ? new Date(row.expires_at) : new Date();
  const t = base.getTime() < Date.now() ? new Date() : base;
  t.setDate(t.getDate() + days);
  const iso = t.toISOString();
  db.prepare('UPDATE wx_groups SET expires_at = ?, is_active = 1 WHERE wx_group_id = ?').run(iso, gid);
  return iso;
}

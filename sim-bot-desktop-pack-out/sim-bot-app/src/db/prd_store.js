import { computeIntegrityHash, verifyIntegrity } from './integrity.js';
import {
  verifyActivationCode,
  activationFingerprint,
  assertPayloadRedeemDeadline,
  getActivationCardSecret,
} from '../auth/activation.js';
import { wxidMatchesPayload } from '../auth/activation-codec.js';
import { extendWxGroupExpiresAt, upsertWxGroupBound } from './wx_groups_store.js';
import {
  getChatroomDisplayMeta,
  resolveChatroomDisplayName,
  syncGroupDisplayMetaFromCache,
} from './chatroom_cache_store.js';
import { formatSqliteUtcForDisplay } from '../util/datetime.js';
import { validateAliasEntry } from '../commands/alias_guard.js';
import { getWechatLoginWxid } from './wechat_login_store.js';
import { isOnlineLicenseValid, getOnlineLicenseExpireDisplay, getOnlineLicense } from './online_license_store.js';

function todayYmdLocal() {
  const d = new Date();
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`;
}

function isProductSetupCompleted(db) {
  const row = db.prepare(`SELECT value FROM app_settings WHERE key = 'product_setup_completed'`).get();
  return row?.value === '1';
}

function addDaysToYmd(ymd, days) {
  const y = Number(String(ymd).slice(0, 4));
  const m = Number(String(ymd).slice(4, 6)) - 1;
  const d = Number(String(ymd).slice(6, 8));
  const t = new Date(y, m, d);
  t.setDate(t.getDate() + days);
  return `${t.getFullYear()}${String(t.getMonth() + 1).padStart(2, '0')}${String(t.getDate()).padStart(2, '0')}`;
}

function formatExpireDisplayYmd(exp) {
  const s = String(exp || '').trim();
  if (!/^\d{8}$/.test(s)) return '—';
  return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`;
}

/** 写入机器人主授权到期日（顶栏「授权」展示用） */
export function seedRobotLicenseDays(db, { wxid, days, last_card_cipher = '' }) {
  const wx = String(wxid || '').trim();
  if (!wx) return null;
  const nDays = Math.min(3660, Math.max(1, Number(days) || 365));
  const cur = getRobotConfig(db);
  let base = todayYmdLocal();
  if (cur?.expire_date && /^\d{8}$/.test(cur.expire_date) && cur.expire_date >= base) {
    base = cur.expire_date;
  }
  const expireDate = addDaysToYmd(base, nDays);
  upsertRobotConfig(db, { wxid: wx, expire_date: expireDate, last_card_cipher });
  return {
    wxid: wx,
    expire_date: expireDate,
    expire_display: formatExpireDisplayYmd(expireDate),
  };
}

/** 已完成产品授权但未写入 robot_config 时，用安装约定天数补主授权（老数据修复） */
export function applyPendingInstallRobotLicense(db) {
  if (!isProductSetupCompleted(db)) return null;
  if (getRobotConfig(db)?.expire_date) return null;
  const wxid = String(getWechatLoginWxid(db) || '').trim();
  if (!wxid) return null;
  const daysRow = db.prepare(`SELECT value FROM app_settings WHERE key = 'install_group_bonus_days'`).get();
  const days = Number(daysRow?.value || 365) || 365;
  return seedRobotLicenseDays(db, { wxid, days, last_card_cipher: '' });
}

export function isRobotLicenseValid(db) {
  if (process.env.SKIP_PRODUCT_SETUP === '1') return true;

  // 优先检查在线授权
  const onlineLic = getOnlineLicense(db);
  if (onlineLic && onlineLic.expires_at) {
    const now = new Date();
    const exp = new Date(onlineLic.expires_at);
    if (exp > now) return true;
  }

  // 回退到离线激活码授权
  const row = getRobotConfig(db);
  if (!row) {
    if (isProductSetupCompleted(db)) return false;
    return true;
  }
  if (!verifyRobotConfigRow(row)) return false;
  const exp = String(row.expire_date || '').trim();
  if (!/^\d{8}$/.test(exp)) return false;
  return exp >= todayYmdLocal();
}

export function recordCardHistory(db, cardNo, targetId) {
  const no = String(cardNo || '').trim();
  const tid = String(targetId || '').trim();
  if (!no || !tid) return;
  db.prepare(
    `INSERT OR IGNORE INTO card_history (card_no, used_at, target_id) VALUES (?, datetime('now'), ?)`
  ).run(no, tid);
}

export function isCardUsed(db, cardNo) {
  const row = db.prepare(`SELECT 1 FROM card_history WHERE card_no = ?`).get(String(cardNo || '').trim());
  return Boolean(row);
}

export function verifyGroupWhitelistRow(db, groupId) {
  const row = db.prepare(`SELECT * FROM group_whitelist WHERE group_id = ?`).get(String(groupId || '').trim());
  if (!row) return true;
  if (!row.integrity_hash) return true;
  return verifyIntegrity(row.expire_datetime, row.last_card_cipher || '', row.integrity_hash);
}

export function redeemGroupCardCipher(db, { wxGroupId, code, publicKeyPem, userId = null }) {
  const gid = String(wxGroupId || '').trim();
  if (!gid || !code) return { error: '缺少群 ID 或卡密' };
  const pem = String(publicKeyPem || '').trim();
  const cardSecret = getActivationCardSecret();
  if (!pem && !cardSecret) return { error: '未配置激活公钥或 ACTIVATION_CARD_SECRET' };
  const robot = getRobotConfig(db);
  const botWxid = String(getWechatLoginWxid(db) || robot?.wxid || '').trim();
  if (!botWxid) return { error: '请先登录微信后再核销群卡' };
  const v = verifyActivationCode({ publicKeyPem: pem || null, cardSecret, wxid: botWxid }, code);
  if (!v.ok) return { error: `卡密无效（${v.reason || 'verify_failed'}）` };
  if (v.payload?.installation === true) {
    return { error: '此为产品安装类授权码，请使用群续期卡密' };
  }
  const dl = assertPayloadRedeemDeadline(v.payload);
  if (!dl.ok) return { error: '该卡密已超过兑换截止时间' };
  const fp = activationFingerprint(code);
  if (isCardUsed(db, fp)) return { error: '该卡密已使用，不能重复核销' };
  const days = Math.min(3660, Math.max(1, Number(v.payload?.days ?? 30) || 30));
  if (!wxidMatchesPayload(v.payload, botWxid)) {
    return { error: '卡密绑定的机器人 wxid 与当前主授权不一致' };
  }
  try {
    db.prepare(
      `INSERT INTO activation_redemptions (code_fingerprint, raw_payload, wx_group_id, redeemed_by_user_id)
       VALUES (?,?,?,?)`
    ).run(fp, JSON.stringify(v.payload), gid, userId);
  } catch {
    return { error: '该卡密已使用' };
  }
  recordCardHistory(db, fp, gid);
  const existed = db.prepare('SELECT id FROM wx_groups WHERE wx_group_id = ?').get(gid);
  if (!existed) {
    upsertWxGroupBound(db, { wx_group_id: gid, strict_play_routes: 1 });
    db.prepare(
      `INSERT OR IGNORE INTO wx_group_route_enables (wx_group_id, guide_word, category_word, is_enabled, updated_at)
       VALUES (?, '新澳门', '特', 1, datetime('now'))`
    ).run(gid);
  }
  const expiresIso = extendWxGroupExpiresAt(db, gid, days);
  syncGroupDisplayMetaFromCache(db, gid);
  const g = db.prepare(`SELECT name, manual_owner FROM wx_groups WHERE wx_group_id = ?`).get(gid);
  const meta = getChatroomDisplayMeta(db, gid);
  extendGroupWhitelist(db, gid, expiresIso.replace('T', ' ').slice(0, 19), code, meta);
  if (g) {
    db.prepare(
      `UPDATE group_whitelist SET group_name = COALESCE(?, group_name), owner_wxid = COALESCE(?, owner_wxid)
       WHERE group_id = ?`
    ).run(g.name || meta.name || '', g.manual_owner || '', gid);
  }
  return {
    ok: true,
    days,
    expires_at: expiresIso,
    expire_display: formatSqliteUtcForDisplay(expiresIso.replace('T', ' ').slice(0, 19)),
    notify_text: `[系统通知] 本群已成功使用卡密续费，有效期延长 ${days} 天，新截止日期为：${formatSqliteUtcForDisplay(expiresIso.replace('T', ' ').slice(0, 19))}。感谢您的支持！`,
  };
}

export function redeemRobotCardCipher(db, { code, publicKeyPem, wxid }) {
  const pem = String(publicKeyPem || '').trim();
  const cardSecret = getActivationCardSecret();
  if (!pem && !cardSecret) return { error: '未配置激活公钥或 ACTIVATION_CARD_SECRET' };
  const targetWxid = String(wxid || '').trim();
  if (!targetWxid) return { error: '缺少机器 wxid' };
  const v = verifyActivationCode(
    { publicKeyPem: pem || null, cardSecret, wxid: targetWxid },
    code
  );
  if (!v.ok) return { error: `卡密无效（${v.reason || 'verify_failed'}）` };
  const dl = assertPayloadRedeemDeadline(v.payload);
  if (!dl.ok) return { error: '该卡密已超过兑换截止时间' };
  const fp = activationFingerprint(code);
  if (isCardUsed(db, fp)) return { error: '该卡密已使用' };
  const days = Math.min(
    3660,
    Math.max(
      1,
      Number(
        v.payload?.installation
          ? v.payload?.group_validity_days ?? v.payload?.days ?? 365
          : v.payload?.days ?? 365
      ) || 365
    )
  );
  if (!wxidMatchesPayload(v.payload, targetWxid)) {
    return { error: '卡密绑定的 wxid 与当前机器码不一致' };
  }
  recordCardHistory(db, fp, targetWxid);
  const seeded = seedRobotLicenseDays(db, {
    wxid: targetWxid,
    days,
    last_card_cipher: code,
  });
  return {
    ok: true,
    wxid: targetWxid,
    expire_date: seeded.expire_date,
    expire_display: seeded.expire_display,
    days,
  };
}

export function getPrdWechatProfile(db) {
  applyPendingInstallRobotLicense(db);
  const robot = getRobotConfig(db);
  const loginWxid = getWechatLoginWxid(db);
  const nick = db.prepare(`SELECT value FROM app_settings WHERE key = 'bot_display_nick'`).get();
  const avatar = db.prepare(`SELECT value FROM app_settings WHERE key = 'bot_display_avatar'`).get();
  const wxid = loginWxid || robot?.wxid || '';

  // 获取在线授权信息
  const onlineLic = getOnlineLicense(db);
  const onlineExpire = getOnlineLicenseExpireDisplay(db);
  const onlineValid = isOnlineLicenseValid(db);

  return {
    wxid,
    login_wxid: loginWxid,
    robot_wxid: robot?.wxid || '',
    nickname: nick?.value || '',
    avatar_url: avatar?.value || '',
    expire_date: robot?.expire_date || '',
    expire_display: formatExpireDisplayYmd(robot?.expire_date),
    // 在线授权信息
    online_auth: onlineLic ? {
      email: onlineLic.email,
      expires_at: onlineLic.expires_at,
      expire_display: onlineExpire,
      valid: onlineValid,
      subscription_type: onlineLic.subscription_type,
      last_sync_at: onlineLic.last_sync_at,
    } : null,
    license_source: onlineValid ? 'online' : (robot?.expire_date ? 'offline' : 'none'),
  };
}

export function listAliasConfig(db, { category } = {}) {
  if (category) {
    return db
      .prepare(
        `SELECT id, category, standard_word, alias_word FROM alias_config WHERE category = ? ORDER BY id DESC`
      )
      .all(category);
  }
  return db
    .prepare(`SELECT id, category, standard_word, alias_word FROM alias_config ORDER BY category, id DESC`)
    .all();
}

export function upsertAliasConfig(db, { id, category, standard_word, alias_word }) {
  const cat = String(category || '').trim();
  const std = String(standard_word || '').trim();
  const alias = String(alias_word || '').trim();
  if (!cat || !std || !alias) throw new Error('category / standard_word / alias_word 必填');
  const guard = validateAliasEntry({ category: cat, standard_word: std, alias_word: alias });
  if (!guard.ok) throw new Error(guard.error);
  if (alias === std) throw new Error('别名不能与标准词相同');
  const dup = db.prepare(`SELECT id FROM alias_config WHERE alias_word = ? AND id != ?`).get(alias, id || 0);
  if (dup) throw new Error(`别名「${alias}」已存在（全局不可重复）`);
  if (cat === 'COLLECTION') {
    const setRow = db
      .prepare(
        `SELECT 1 FROM cmd_collections
         WHERE set_name = ? AND is_active = 1
           AND (wx_group_id IS NULL OR trim(coalesce(wx_group_id,'')) = '')
         LIMIT 1`
      )
      .get(std);
    if (!setRow) throw new Error(`合集「${std}」不存在，请先在合集管理中创建`);
  }
  if (id) {
    db.prepare(
      `UPDATE alias_config SET category = ?, standard_word = ?, alias_word = ? WHERE id = ?`
    ).run(cat, std, alias, id);
    return { id };
  }
  const r = db
    .prepare(`INSERT INTO alias_config (category, standard_word, alias_word) VALUES (?,?,?)`)
    .run(cat, std, alias);
  return { id: r.lastInsertRowid };
}

export function deleteAliasConfig(db, id) {
  db.prepare(`DELETE FROM alias_config WHERE id = ?`).run(id);
}

export function deleteAliasConfigByAliasWord(db, { category, alias_word }) {
  const cat = String(category || '').trim();
  const alias = String(alias_word || '').trim();
  if (!cat || !alias) return;
  const row = db
    .prepare(`SELECT id FROM alias_config WHERE category = ? AND alias_word = ?`)
    .get(cat, alias);
  if (row?.id) deleteAliasConfig(db, row.id);
}

export function getRobotConfig(db) {
  return db.prepare(`SELECT * FROM robot_config LIMIT 1`).get();
}

export function upsertRobotConfig(db, { wxid, expire_date, last_card_cipher }) {
  const wx = String(wxid || '').trim();
  const exp = String(expire_date || '').trim();
  const cipher = String(last_card_cipher || '');
  if (!wx || !exp) throw new Error('wxid / expire_date 必填');
  const integrity_hash = computeIntegrityHash(exp, cipher);
  db.prepare(
    `INSERT INTO robot_config (wxid, expire_date, last_card_cipher, integrity_hash)
     VALUES (?,?,?,?)
     ON CONFLICT(wxid) DO UPDATE SET
       expire_date = excluded.expire_date,
       last_card_cipher = excluded.last_card_cipher,
       integrity_hash = excluded.integrity_hash`
  ).run(wx, exp, cipher, integrity_hash);
  return { wxid: wx, expire_date: exp, integrity_hash };
}

export function verifyRobotConfigRow(row) {
  if (!row) return false;
  return verifyIntegrity(row.expire_date, row.last_card_cipher || '', row.integrity_hash);
}

export function listGroupsNearingExpiry(db, days = 7) {
  const d = Math.max(1, Number(days) || 7);
  return db
    .prepare(
      `SELECT g.*,
        CAST((julianday(COALESCE(g.expires_at, w.expire_datetime)) - julianday('now')) AS INTEGER) AS days_left
       FROM wx_groups g
       LEFT JOIN group_whitelist w ON w.group_id = g.wx_group_id
       WHERE g.is_active = 1
         AND COALESCE(g.expires_at, w.expire_datetime) IS NOT NULL
         AND julianday(COALESCE(g.expires_at, w.expire_datetime)) - julianday('now') BETWEEN 0 AND ?
       ORDER BY days_left ASC`
    )
    .all(d);
}

/** 群管理台：Hook 缓存中的全部群 + 是否已绑定（wx_groups.is_active=1） */
export function listPrdGroupDeskRows(db) {
  const bound = listPrdGroups(db);
  const boundIds = new Set(bound.map((g) => String(g.wx_group_id || '').trim()));
  const boundById = new Map(bound.map((g) => [String(g.wx_group_id || '').trim(), g]));

  let cacheRows = [];
  try {
    cacheRows = db
      .prepare(
        `SELECT room_id, nick_name, remark, member_count, owner_wxid, updated_at
         FROM wx_chatroom_cache
         WHERE room_id LIKE '%@chatroom'
         ORDER BY updated_at DESC, room_id ASC`
      )
      .all();
  } catch {
    cacheRows = [];
  }

  const out = [];
  const seen = new Set();
  for (const c of cacheRows) {
    const id = String(c.room_id || '').trim();
    if (!id || seen.has(id)) continue;
    seen.add(id);
    const b = boundById.get(id);
    const name =
      (b && String(b.name || '').trim()) ||
      String(c.nick_name || c.remark || '').trim() ||
      id;
    out.push({
      wx_group_id: id,
      name,
      is_bound: boundIds.has(id),
      owner_wxid: b?.owner_wxid || c.owner_wxid || '',
      member_count: b?.member_count ?? c.member_count ?? 0,
      expire_display: b?.expire_display || '—',
      days_left: b?.days_left ?? null,
      service_expire: b?.service_expire || null,
      cache_updated_at: c.updated_at || null,
    });
  }
  for (const g of bound) {
    const id = String(g.wx_group_id || '').trim();
    if (!id || seen.has(id)) continue;
    seen.add(id);
    out.push({
      wx_group_id: id,
      name: g.name || id,
      is_bound: true,
      owner_wxid: g.owner_wxid || '',
      member_count: g.member_count ?? 0,
      expire_display: g.expire_display || '—',
      days_left: g.days_left ?? null,
      service_expire: g.service_expire || null,
      cache_updated_at: null,
    });
  }
  out.sort((a, b) => {
    if (a.is_bound !== b.is_bound) return a.is_bound ? -1 : 1;
    return String(a.name || '').localeCompare(String(b.name || ''), 'zh-CN');
  });
  return out;
}

/** 群管理台列表指纹：绑定状态 / 到期等变化时 revision 会变（供心跳轮询刷新） */
export function computeGroupsDeskRevision(db) {
  const rows = listPrdGroupDeskRows(db);
  const parts = rows.map(
    (r) =>
      `${r.wx_group_id}|${r.is_bound ? 1 : 0}|${r.expire_display || ''}|${r.days_left ?? ''}|${r.name || ''}`
  );
  let h = 0;
  const s = parts.join('\n');
  for (let i = 0; i < s.length; i++) {
    h = (Math.imul(31, h) + s.charCodeAt(i)) | 0;
  }
  return `${rows.length}:${(h >>> 0).toString(16)}`;
}

export function listPrdGroups(db) {
  return db
    .prepare(
      `SELECT
         g.wx_group_id,
         COALESCE(
           NULLIF(TRIM(g.name), ''),
           NULLIF(TRIM(c.nick_name), ''),
           NULLIF(TRIM(c.remark), ''),
           NULLIF(TRIM(w.group_name), ''),
           ''
         ) AS name,
         COALESCE(NULLIF(TRIM(w.owner_wxid), ''), g.manual_owner, '') AS owner_wxid,
         COALESCE(
           NULLIF(c.member_count, 0),
           NULLIF(w.member_count, 0),
           m.member_count,
           0
         ) AS member_count,
         COALESCE(g.expires_at, w.expire_datetime) AS service_expire,
         CAST(
           (julianday(COALESCE(g.expires_at, w.expire_datetime)) - julianday('now')) AS INTEGER
         ) AS days_left,
         g.is_active,
         g.strict_play_routes,
         w.integrity_hash AS whitelist_integrity
       FROM wx_groups g
       LEFT JOIN group_whitelist w ON w.group_id = g.wx_group_id
       LEFT JOIN wx_chatroom_cache c ON c.room_id = g.wx_group_id
       LEFT JOIN (
         SELECT room_id, COUNT(*) AS member_count
         FROM wx_chatroom_members
         GROUP BY room_id
       ) m ON m.room_id = g.wx_group_id
       WHERE g.is_active = 1
       ORDER BY g.id DESC`
    )
    .all()
    .map((r) => {
      const displayName = resolveChatroomDisplayName(db, r.wx_group_id) || String(r.name || '').trim();
      return {
        ...r,
        name: displayName,
        expire_display: r.service_expire ? formatSqliteUtcForDisplay(r.service_expire) : '—',
        days_left:
          r.service_expire != null && r.days_left != null && Number.isFinite(Number(r.days_left))
            ? Number(r.days_left)
            : null,
      };
    });
}

export function isGroupServiceValid(db, wxGroupId) {
  const gid = String(wxGroupId || '').trim();
  if (!gid) return true;
  const row = db
    .prepare(
      `SELECT g.expires_at, w.expire_datetime, w.integrity_hash, w.last_card_cipher
       FROM wx_groups g
       LEFT JOIN group_whitelist w ON w.group_id = g.wx_group_id
       WHERE g.wx_group_id = ? AND g.is_active = 1`
    )
    .get(gid);
  if (!row) return false;
  if (row.integrity_hash) {
    const exp = row.expire_datetime || row.expires_at || '';
    if (!verifyIntegrity(exp, row.last_card_cipher || '', row.integrity_hash)) return false;
  }
  const expRaw = row.expires_at || row.expire_datetime;
  if (!expRaw) return true;
  const exp = new Date(String(expRaw).replace(' ', 'T')).getTime();
  return !Number.isFinite(exp) || exp >= Date.now();
}

export function extendGroupWhitelist(db, groupId, newExpireIso, cardCipher = '', meta = {}) {
  const gid = String(groupId || '').trim();
  const hash = computeIntegrityHash(newExpireIso, cardCipher);
  const groupName = String(meta.group_name || '').trim();
  const memberCount = Math.max(0, Number(meta.member_count || 0) || 0);
  db.prepare(
    `INSERT INTO group_whitelist (group_id, group_name, owner_wxid, member_count, expire_datetime, last_card_cipher, integrity_hash)
     VALUES (?, ?, '', ?, ?, ?, ?)
     ON CONFLICT(group_id) DO UPDATE SET
       expire_datetime = excluded.expire_datetime,
       last_card_cipher = excluded.last_card_cipher,
       integrity_hash = excluded.integrity_hash,
       group_name = CASE
         WHEN TRIM(excluded.group_name) <> '' THEN excluded.group_name
         ELSE group_whitelist.group_name
       END,
       member_count = CASE
         WHEN excluded.member_count > 0 THEN excluded.member_count
         ELSE group_whitelist.member_count
       END`
  ).run(gid, groupName, memberCount, newExpireIso, cardCipher, hash);
}

/**
 * 在线授权本地存储
 * 管理从云端获取的授权信息的增删改查
 */

export function getOnlineLicense(db) {
  return db.prepare('SELECT * FROM online_license WHERE id = 1').get() || null;
}

export function upsertOnlineLicense(db, { user_id, email, auth_token, expires_at, subscription_type, max_groups }) {
  const uid = Number(user_id) || 0;
  const em = String(email || '').trim();
  const tok = String(auth_token || '');
  const exp = String(expires_at || '').trim();
  const sub = String(subscription_type || 'monthly').trim();
  const mg = Math.max(0, Number(max_groups) || 3);

  if (!uid || !em || !exp) throw new Error('user_id/email/expires_at 必填');

  const existing = getOnlineLicense(db);
  if (existing) {
    db.prepare(`
      UPDATE online_license SET
        user_id = ?, email = ?, auth_token = ?, expires_at = ?,
        subscription_type = ?, max_groups = ?, updated_at = datetime('now')
      WHERE id = 1
    `).run(uid, em, tok, exp, sub, mg);
  } else {
    db.prepare(`
      INSERT INTO online_license (id, user_id, email, auth_token, expires_at, subscription_type, max_groups)
      VALUES (1, ?, ?, ?, ?, ?, ?)
    `).run(uid, em, tok, exp, sub, mg);
  }

  return getOnlineLicense(db);
}

export function updateOnlineLicenseSyncAt(db) {
  db.prepare(`
    UPDATE online_license SET last_sync_at = datetime('now'), updated_at = datetime('now') WHERE id = 1
  `).run();
}

export function clearOnlineLicense(db) {
  db.prepare('DELETE FROM online_license').run();
}

export function isOnlineLicenseValid(db) {
  const lic = getOnlineLicense(db);
  if (!lic) return false;
  const exp = String(lic.expires_at || '').trim();
  if (!exp) return false;
  const expireTime = new Date(exp);
  if (isNaN(expireTime.getTime())) return false;
  return expireTime > new Date();
}

export function getOnlineLicenseDaysRemaining(db) {
  const lic = getOnlineLicense(db);
  if (!lic) return 0;
  const exp = String(lic.expires_at || '').trim();
  if (!exp) return 0;
  const now = new Date();
  const expireTime = new Date(exp);
  if (expireTime <= now) return 0;
  return Math.ceil((expireTime - now) / (1000 * 60 * 60 * 24));
}

export function getOnlineLicenseExpireDisplay(db) {
  const lic = getOnlineLicense(db);
  if (!lic) return '—';
  const exp = String(lic.expires_at || '').trim();
  if (!exp) return '—';
  const d = new Date(exp);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}
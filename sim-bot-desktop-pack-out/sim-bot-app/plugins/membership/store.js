export const membershipStore = {
  async init(db) {
    await db.exec(`CREATE TABLE IF NOT EXISTS shop_membership_cards (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      card_no TEXT UNIQUE NOT NULL,
      customer_name TEXT NOT NULL,
      customer_phone TEXT,
      customer_wxid TEXT,
      total_services INTEGER DEFAULT 0,
      used_services INTEGER DEFAULT 0,
      remaining_services INTEGER DEFAULT 0,
      start_date TEXT,
      expire_date TEXT,
      status TEXT DEFAULT 'active',
      notes TEXT,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )`);
    await db.exec(`CREATE TABLE IF NOT EXISTS shop_membership_usage (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      card_id INTEGER NOT NULL,
      service_id INTEGER,
      service_name TEXT,
      notes TEXT,
      used_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (card_id) REFERENCES shop_membership_cards(id)
    )`);
    await db.exec(`CREATE INDEX IF NOT EXISTS idx_member_card_no ON shop_membership_cards(card_no)`);
    await db.exec(`CREATE INDEX IF NOT EXISTS idx_member_card_wxid ON shop_membership_cards(customer_wxid)`);
  },

  getAll(db, params = {}) {
    const { status, customer_wxid, keyword, page = 1, pageSize = 20 } = params;
    const conditions = [];
    const args = [];
    if (status) { conditions.push('status = ?'); args.push(status); }
    if (customer_wxid) { conditions.push('customer_wxid = ?'); args.push(customer_wxid); }
    if (keyword) {
      conditions.push('(card_no LIKE ? OR customer_name LIKE ? OR customer_phone LIKE ?)');
      const kw = `%${keyword}%`;
      args.push(kw, kw, kw);
    }
    const where = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
    const offset = (Math.max(1, page) - 1) * Math.max(1, pageSize);
    const limit = Math.max(1, pageSize);
    const items = db.prepare(`SELECT * FROM shop_membership_cards ${where} ORDER BY id DESC LIMIT ? OFFSET ?`).all(...args, limit, offset);
    const total = db.prepare(`SELECT COUNT(*) AS n FROM shop_membership_cards ${where}`).get(...args);
    return { items, total: total?.n || 0, page, pageSize };
  },

  getById(db, id) {
    return db.prepare(`SELECT * FROM shop_membership_cards WHERE id = ?`).get(id);
  },

  getByNo(db, cardNo) {
    return db.prepare(`SELECT * FROM shop_membership_cards WHERE card_no = ?`).get(String(cardNo || '').trim());
  },

  create(db, data) {
    const no = String(data.card_no || '').trim();
    const name = String(data.customer_name || '').trim();
    if (!no) throw new Error('Card number cannot be empty');
    if (!name) throw new Error('Customer name cannot be empty');
    const total = Math.max(1, Number(data.total_services) || 1);
    const dup = db.prepare(`SELECT id FROM shop_membership_cards WHERE card_no = ?`).get(no);
    if (dup) throw new Error(`Card number "${no}" already exists`);
    const r = db.prepare(`INSERT INTO shop_membership_cards (card_no, customer_name, customer_phone, customer_wxid, total_services, used_services, remaining_services, start_date, expire_date, notes) VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?)`).run(no, name, String(data.customer_phone || ''), String(data.customer_wxid || ''), total, total, data.start_date || null, data.expire_date || null, String(data.notes || ''));
    return { id: r.lastInsertRowid };
  },

  use(db, id, serviceId, serviceName, notes = '') {
    const card = this.getById(db, id);
    if (!card) throw new Error('Membership card not found');
    if (card.status !== 'active') throw new Error('Membership card is inactive');
    if (card.remaining_services <= 0) throw new Error('Insufficient remaining services');
    const newUsed = card.used_services + 1;
    const newRemaining = card.total_services - newUsed;
    db.prepare(`UPDATE shop_membership_cards SET used_services = ?, remaining_services = ?, updated_at = datetime('now') WHERE id = ?`).run(newUsed, newRemaining, id);
    const svcName = String(serviceName || '').trim() || null;
    db.prepare(`INSERT INTO shop_membership_usage (card_id, service_id, service_name, notes) VALUES (?, ?, ?, ?)`).run(id, serviceId || null, svcName, String(notes || ''));
    return { ok: true, card_no: card.card_no, customer_name: card.customer_name, total_services: card.total_services, used_services: newUsed, remaining_services: newRemaining };
  },

  getUsageHistory(db, cardId) {
    return db.prepare(`SELECT * FROM shop_membership_usage WHERE card_id = ? ORDER BY used_at DESC`).all(cardId);
  },

  update(db, id, data) {
    const existing = db.prepare(`SELECT * FROM shop_membership_cards WHERE id = ?`).get(id);
    if (!existing) throw new Error('Membership card not found');
    const customer_name = data.customer_name !== undefined ? String(data.customer_name).trim() : existing.customer_name;
    const customer_phone = data.customer_phone !== undefined ? String(data.customer_phone).trim() : existing.customer_phone;
    const status = data.status !== undefined ? data.status : existing.status;
    const notes = data.notes !== undefined ? String(data.notes).trim() : existing.notes;
    db.prepare(`UPDATE shop_membership_cards SET customer_name = ?, customer_phone = ?, status = ?, notes = ?, updated_at = datetime('now') WHERE id = ?`).run(customer_name, customer_phone, status, notes, id);
    return { ok: true };
  },
};

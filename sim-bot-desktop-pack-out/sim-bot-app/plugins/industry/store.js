import { knowledgeStore } from '../knowledge-base/store.js';

export const industryStore = {
  async init(db) {
    await db.exec(`CREATE TABLE IF NOT EXISTS shop_info (
      id INTEGER PRIMARY KEY CHECK (id = 1),
      name TEXT NOT NULL DEFAULT '',
      address TEXT NOT NULL DEFAULT '',
      latitude REAL DEFAULT 0,
      longitude REAL DEFAULT 0,
      phone TEXT DEFAULT '',
      business_hours TEXT DEFAULT '',
      description TEXT DEFAULT '',
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )`);
    await db.exec(`INSERT OR IGNORE INTO shop_info (id, name) VALUES (1, '')`);

    await db.exec(`CREATE TABLE IF NOT EXISTS shop_services (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      category TEXT DEFAULT '',
      duration_minutes INTEGER DEFAULT 60,
      price REAL DEFAULT 0,
      original_price REAL DEFAULT 0,
      description TEXT DEFAULT '',
      is_active INTEGER DEFAULT 1,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )`);

    await db.exec(`CREATE TABLE IF NOT EXISTS shop_pending_questions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      question TEXT NOT NULL,
      answer TEXT,
      asker_name TEXT DEFAULT '',
      asker_wxid TEXT DEFAULT '',
      status TEXT DEFAULT 'pending',
      answered_at TEXT,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )`);
  },

  // ==================== 店铺信息 ====================

  getShopInfo(db) {
    return db.prepare(`SELECT * FROM shop_info WHERE id = 1`).get();
  },

  upsertShopInfo(db, info) {
    const existing = db.prepare(`SELECT id FROM shop_info WHERE id = 1`).get();
    const sql = existing
      ? `UPDATE shop_info SET name = ?, address = ?, latitude = ?, longitude = ?, phone = ?, business_hours = ?, description = ?, updated_at = datetime('now') WHERE id = 1`
      : `INSERT INTO shop_info (id, name, address, latitude, longitude, phone, business_hours, description) VALUES (1, ?, ?, ?, ?, ?, ?, ?)`;
    db.prepare(sql).run(
      String(info.name || ''),
      String(info.address || ''),
      Number(info.latitude || 0),
      Number(info.longitude || 0),
      String(info.phone || ''),
      String(info.business_hours || ''),
      String(info.description || '')
    );
    return { ok: true };
  },

  // ==================== 服务项目 ====================

  listServices(db, { category, is_active, page = 1, pageSize = 50 } = {}) {
    const conditions = [];
    const params = [];
    if (category) { conditions.push('category = ?'); params.push(category); }
    if (is_active !== undefined) { conditions.push('is_active = ?'); params.push(is_active ? 1 : 0); }
    const where = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
    const offset = (Math.max(1, page) - 1) * Math.max(1, pageSize);
    const limit = Math.max(1, pageSize);
    const items = db.prepare(`SELECT * FROM shop_services ${where} ORDER BY category, id ASC LIMIT ? OFFSET ?`).all(...params, limit, offset);
    const totalRow = db.prepare(`SELECT COUNT(*) AS n FROM shop_services ${where}`).get(...params);
    return { items, total: totalRow?.n || 0, page, pageSize };
  },

  getServiceById(db, id) {
    return db.prepare(`SELECT * FROM shop_services WHERE id = ?`).get(id);
  },

  createService(db, data) {
    const name = String(data.name || '').trim();
    if (!name) throw new Error('服务名称不能为空');
    const r = db.prepare(`INSERT INTO shop_services (name, category, duration_minutes, price, original_price, description) VALUES (?, ?, ?, ?, ?, ?)`).run(
      name,
      String(data.category || '').trim(),
      Math.max(1, Number(data.duration_minutes) || 60),
      Math.max(0, Number(data.price) || 0),
      Math.max(0, Number(data.original_price) || 0),
      String(data.description || '').trim()
    );
    return { id: r.lastInsertRowid };
  },

  updateService(db, id, updates) {
    const existing = db.prepare(`SELECT * FROM shop_services WHERE id = ?`).get(id);
    if (!existing) throw new Error('服务项目不存在');
    const name = updates.name !== undefined ? String(updates.name).trim() : existing.name;
    const category = updates.category !== undefined ? String(updates.category).trim() : existing.category;
    const duration = updates.duration_minutes !== undefined ? Math.max(1, Number(updates.duration_minutes) || 60) : existing.duration_minutes;
    const price = updates.price !== undefined ? Math.max(0, Number(updates.price) || 0) : existing.price;
    const originalPrice = updates.original_price !== undefined ? Math.max(0, Number(updates.original_price) || 0) : existing.original_price;
    const description = updates.description !== undefined ? String(updates.description).trim() : existing.description;
    const isActive = updates.is_active !== undefined ? (updates.is_active ? 1 : 0) : existing.is_active;
    db.prepare(`UPDATE shop_services SET name = ?, category = ?, duration_minutes = ?, price = ?, original_price = ?, description = ?, is_active = ?, updated_at = datetime('now') WHERE id = ?`).run(name, category, duration, price, originalPrice, description, isActive, id);
    return { ok: true };
  },

  deleteService(db, id) {
    db.prepare(`DELETE FROM shop_services WHERE id = ?`).run(id);
  },

  // ==================== 待回答问题 ====================

  createPendingQuestion(db, data) {
    const q = String(data.question || '').trim();
    if (!q) throw new Error('问题不能为空');
    const r = db.prepare(`INSERT INTO shop_pending_questions (question, asker_name, asker_wxid) VALUES (?, ?, ?)`).run(q, String(data.asker_name || ''), String(data.asker_wxid || ''));
    return { id: r.lastInsertRowid };
  },

  listPendingQuestions(db, { status = 'pending', page = 1, pageSize = 20 } = {}) {
    const offset = (Math.max(1, page) - 1) * Math.max(1, pageSize);
    const limit = Math.max(1, pageSize);
    const items = db.prepare(`SELECT * FROM shop_pending_questions WHERE status = ? ORDER BY id DESC LIMIT ? OFFSET ?`).all(status, limit, offset);
    const totalRow = db.prepare(`SELECT COUNT(*) AS n FROM shop_pending_questions WHERE status = ?`).get(status);
    return { items, total: totalRow?.n || 0, page, pageSize };
  },

  /** 回答提问，同时通过 knowledgeStore 写入知识库（解耦：不直接写 shop_knowledge_base） */
  answerPendingQuestion(db, id, answer) {
    const existing = db.prepare(`SELECT * FROM shop_pending_questions WHERE id = ? AND status = 'pending'`).get(id);
    if (!existing) throw new Error('问题不存在或已回答');
    const a = String(answer || '').trim();
    if (!a) throw new Error('回答内容不能为空');
    db.prepare(`UPDATE shop_pending_questions SET status = 'answered', answer = ?, answered_at = datetime('now') WHERE id = ?`).run(a, id);
    // 通过 knowledgeStore 写入知识库（解耦：不直接写 shop_knowledge_base）
    knowledgeStore.create(db, { question: existing.question, answer: a, category: 'boss' });
    return { ok: true, question: existing.question, answer: a };
  },
};
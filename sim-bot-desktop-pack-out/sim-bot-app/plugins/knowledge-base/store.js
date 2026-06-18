export const knowledgeStore = {
  async init(db) {
    await db.exec(`CREATE TABLE IF NOT EXISTS shop_knowledge_base (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      question TEXT NOT NULL,
      answer TEXT NOT NULL,
      category TEXT DEFAULT 'custom',
      is_active INTEGER DEFAULT 1,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )`);
    await db.exec(`CREATE INDEX IF NOT EXISTS idx_knowledge_category ON shop_knowledge_base(category)`);
  },

  search(db, keyword, limit = 10) {
    const kw = `%${String(keyword || '').trim()}%`;
    return db.prepare(`SELECT * FROM shop_knowledge_base WHERE is_active = 1 AND (question LIKE ? OR answer LIKE ?) ORDER BY id DESC LIMIT ?`).all(kw, kw, limit);
  },

  getAll(db, params = {}) {
    const { category, page = 1, pageSize = 20 } = params;
    const offset = (Math.max(1, page) - 1) * Math.max(1, pageSize);
    const limit = Math.max(1, pageSize);
    if (category) {
      const items = db.prepare(`SELECT * FROM shop_knowledge_base WHERE category = ? ORDER BY id DESC LIMIT ? OFFSET ?`).all(category, limit, offset);
      const total = db.prepare(`SELECT COUNT(*) AS n FROM shop_knowledge_base WHERE category = ?`).get(category);
      return { items, total: total?.n || 0, page, pageSize };
    }
    const items = db.prepare(`SELECT * FROM shop_knowledge_base ORDER BY id DESC LIMIT ? OFFSET ?`).all(limit, offset);
    const total = db.prepare(`SELECT COUNT(*) AS n FROM shop_knowledge_base`).get();
    return { items, total: total?.n || 0, page, pageSize };
  },

  create(db, data) {
    const q = String(data.question || '').trim();
    const a = String(data.answer || '').trim();
    const c = String(data.category || 'custom').trim();
    if (!q || !a) throw new Error('question and answer cannot be empty');
    const r = db.prepare(`INSERT INTO shop_knowledge_base (question, answer, category) VALUES (?, ?, ?)`).run(q, a, c);
    return { id: r.lastInsertRowid };
  },

  update(db, id, data) {
    const existing = db.prepare(`SELECT * FROM shop_knowledge_base WHERE id = ?`).get(id);
    if (!existing) throw new Error('Knowledge item not found');
    const q = data.question !== undefined ? String(data.question).trim() : existing.question;
    const a = data.answer !== undefined ? String(data.answer).trim() : existing.answer;
    const c = data.category !== undefined ? String(data.category).trim() : existing.category;
    const act = data.is_active !== undefined ? (data.is_active ? 1 : 0) : existing.is_active;
    db.prepare(`UPDATE shop_knowledge_base SET question = ?, answer = ?, category = ?, is_active = ?, updated_at = datetime('now') WHERE id = ?`).run(q, a, c, act, id);
    return { ok: true };
  },

  delete(db, id) {
    db.prepare(`DELETE FROM shop_knowledge_base WHERE id = ?`).run(id);
  },
};

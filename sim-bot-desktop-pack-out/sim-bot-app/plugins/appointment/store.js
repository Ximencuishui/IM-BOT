export const appointmentStore = {
  async init(db) {
    await db.exec(`CREATE TABLE IF NOT EXISTS shop_appointments (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      customer_name TEXT NOT NULL,
      customer_phone TEXT DEFAULT '',
      customer_wxid TEXT DEFAULT '',
      service_id INTEGER,
      staff_name TEXT DEFAULT '',
      appointment_date TEXT NOT NULL,
      start_time TEXT NOT NULL,
      end_time TEXT NOT NULL,
      status TEXT DEFAULT 'pending',
      notes TEXT DEFAULT '',
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )`);
    await db.exec(`CREATE INDEX IF NOT EXISTS idx_appt_date ON shop_appointments(appointment_date)`);
    await db.exec(`CREATE INDEX IF NOT EXISTS idx_appt_wxid ON shop_appointments(customer_wxid)`);
  },

  getAvailableSlots(db, date, duration = 60) {
    const slots = [];
    for (let h = 8; h < 22; h++) {
      slots.push(`${String(h).padStart(2, '0')}:00`);
      slots.push(`${String(h).padStart(2, '0')}:30`);
    }
    const booked = db.prepare(`SELECT start_time, end_time FROM shop_appointments WHERE appointment_date = ? AND status IN ('pending','confirmed')`).all(date);
    const bookedSet = new Set();
    for (const b of booked) {
      const startIdx = slots.indexOf(b.start_time);
      if (startIdx === -1) continue;
      const slotsNeeded = Math.ceil(duration / 30);
      for (let i = 0; i < slotsNeeded; i++) {
        if (startIdx + i < slots.length) bookedSet.add(slots[startIdx + i]);
      }
    }
    const available = [];
    for (let i = 0; i < slots.length; i++) {
      const slotsNeeded = Math.ceil(duration / 30);
      let canBook = true;
      for (let j = 0; j < slotsNeeded; j++) {
        if (i + j >= slots.length || bookedSet.has(slots[i + j])) { canBook = false; break; }
      }
      if (canBook) {
        const endMinutes = parseInt(slots[i].split(':')[0]) * 60 + parseInt(slots[i].split(':')[1]) + duration;
        const endTime = `${String(Math.floor(endMinutes / 60)).padStart(2, '0')}:${String(endMinutes % 60).padStart(2, '0')}`;
        available.push({ start_time: slots[i], end_time: endTime });
        i += slotsNeeded - 1;
      }
    }
    return available;
  },

  getAll(db, { date, status, customer_wxid, page = 1, pageSize = 20 } = {}) {
    const conditions = [];
    const args = [];
    if (date) { conditions.push('appointment_date = ?'); args.push(date); }
    if (status) { conditions.push('status = ?'); args.push(status); }
    if (customer_wxid) { conditions.push('customer_wxid = ?'); args.push(customer_wxid); }
    const where = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
    const offset = (Math.max(1, page) - 1) * Math.max(1, pageSize);
    const limit = Math.max(1, pageSize);
    const items = db.prepare(`SELECT * FROM shop_appointments ${where} ORDER BY appointment_date DESC, start_time ASC LIMIT ? OFFSET ?`).all(...args, limit, offset);
    const total = db.prepare(`SELECT COUNT(*) AS n FROM shop_appointments ${where}`).get(...args);
    return { items, total: total?.n || 0, page, pageSize };
  },

  create(db, data) {
    const name = String(data.customer_name || '').trim();
    if (!name) throw new Error('Customer name is required');
    const date = String(data.appointment_date || '').trim();
    const start = String(data.start_time || '').trim();
    const end = String(data.end_time || '').trim();
    if (!date || !start || !end) throw new Error('Appointment time is required');
    // check conflict
    const conflict = db.prepare(`SELECT id FROM shop_appointments WHERE appointment_date = ? AND status IN ('pending','confirmed') AND start_time < ? AND end_time > ?`).get(date, end, start);
    if (conflict) throw new Error('Time slot already booked');
    const r = db.prepare(`INSERT INTO shop_appointments (customer_name, customer_phone, customer_wxid, service_id, staff_name, appointment_date, start_time, end_time, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`).run(
      name, String(data.customer_phone || ''), String(data.customer_wxid || ''), data.service_id || null, String(data.staff_name || ''), date, start, end, String(data.notes || '')
    );
    return { id: r.lastInsertRowid };
  },

  updateStatus(db, id, status) {
    if (!['pending', 'confirmed', 'completed', 'cancelled'].includes(status)) throw new Error('Invalid status');
    const existing = db.prepare(`SELECT id FROM shop_appointments WHERE id = ?`).get(id);
    if (!existing) throw new Error('Appointment not found');
    db.prepare(`UPDATE shop_appointments SET status = ?, updated_at = datetime('now') WHERE id = ?`).run(status, id);
    return { ok: true };
  },

  update(db, id, data) {
    const existing = db.prepare(`SELECT * FROM shop_appointments WHERE id = ?`).get(id);
    if (!existing) throw new Error('Appointment not found');
    db.prepare(`UPDATE shop_appointments SET customer_name = ?, customer_phone = ?, appointment_date = ?, start_time = ?, end_time = ?, status = ?, notes = ?, updated_at = datetime('now') WHERE id = ?`).run(
      data.customer_name !== undefined ? String(data.customer_name).trim() : existing.customer_name,
      data.customer_phone !== undefined ? String(data.customer_phone).trim() : existing.customer_phone,
      data.appointment_date !== undefined ? String(data.appointment_date).trim() : existing.appointment_date,
      data.start_time !== undefined ? String(data.start_time).trim() : existing.start_time,
      data.end_time !== undefined ? String(data.end_time).trim() : existing.end_time,
      data.status !== undefined ? data.status : existing.status,
      data.notes !== undefined ? String(data.notes).trim() : existing.notes,
      id
    );
    return { ok: true };
  },

  delete(db, id) {
    db.prepare(`DELETE FROM shop_appointments WHERE id = ?`).run(id);
  },
};
import express from 'express';
import { appointmentStore } from './store.js';

export function createRouter(ctx) {
  const router = express.Router();
  const { db } = ctx;

  router.get('/slots', (req, res) => {
    const { date, duration } = req.query;
    if (!date) return res.status(400).json({ error: 'date is required' });
    const slots = appointmentStore.getAvailableSlots(db, date, Number(duration) || 60);
    res.json({ items: slots, date });
  });

  router.get('/', (req, res) => {
    const { date, status, customer_wxid, page, pageSize } = req.query;
    res.json(appointmentStore.getAll(db, {
      date, status, customer_wxid,
      page: Number(page) || 1,
      pageSize: Number(pageSize) || 20,
    }));
  });

  router.post('/', (req, res) => {
    try {
      res.json({ ok: true, ...appointmentStore.create(db, req.body || {}) });
    } catch (e) {
      res.status(400).json({ error: String(e?.message || e) });
    }
  });

  router.put('/:id', (req, res) => {
    try {
      appointmentStore.update(db, Number(req.params.id), req.body || {});
      res.json({ ok: true });
    } catch (e) {
      res.status(400).json({ error: String(e?.message || e) });
    }
  });

  router.put('/:id/status', (req, res) => {
    try {
      appointmentStore.updateStatus(db, Number(req.params.id), req.body?.status);
      res.json({ ok: true });
    } catch (e) {
      res.status(400).json({ error: String(e?.message || e) });
    }
  });

  router.delete('/:id', (req, res) => {
    appointmentStore.delete(db, Number(req.params.id));
    res.json({ ok: true });
  });

  return router;
}
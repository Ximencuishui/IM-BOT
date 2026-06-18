import express from 'express';
import { membershipStore } from './store.js';

export function createRouter(ctx) {
  const router = express.Router();
  const { db } = ctx;

  router.get('/', (req, res) => {
    const { status, customer_wxid, keyword, page, pageSize } = req.query;
    res.json(membershipStore.getAll(db, { status, customer_wxid, keyword, page: Number(page) || 1, pageSize: Number(pageSize) || 20 }));
  });

  router.get('/:id', (req, res) => {
    const card = membershipStore.getById(db, Number(req.params.id));
    res.json(card ? { card } : { error: 'Membership card not found' });
  });

  router.post('/', (req, res) => {
    try {
      res.json({ ok: true, ...membershipStore.create(db, req.body || {}) });
    } catch (e) {
      res.status(400).json({ error: String(e?.message || e) });
    }
  });

  router.post('/:id/use', (req, res) => {
    try {
      res.json(membershipStore.use(db, Number(req.params.id), req.body?.service_id, req.body?.service_name, req.body?.notes));
    } catch (e) {
      res.status(400).json({ error: String(e?.message || e) });
    }
  });

  router.get('/:id/usage', (req, res) => {
    res.json({ items: membershipStore.getUsageHistory(db, Number(req.params.id)) });
  });

  router.put('/:id', (req, res) => {
    try {
      membershipStore.update(db, Number(req.params.id), req.body || {});
      res.json({ ok: true });
    } catch (e) {
      res.status(400).json({ error: String(e?.message || e) });
    }
  });

  return router;
}

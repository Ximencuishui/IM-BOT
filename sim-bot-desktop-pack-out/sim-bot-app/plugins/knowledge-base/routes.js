import express from 'express';
import { knowledgeStore } from './store.js';

export function createRouter(ctx) {
  const router = express.Router();
  const { db } = ctx;

  router.get('/', (req, res) => {
    const { category, page, pageSize } = req.query;
    res.json(knowledgeStore.getAll(db, { category, page: Number(page) || 1, pageSize: Number(pageSize) || 20 }));
  });

  router.get('/search', (req, res) => {
    const keyword = String(req.query.keyword || '').trim();
    res.json({ items: keyword ? knowledgeStore.search(db, keyword, Number(req.query.limit) || 10) : [] });
  });

  router.post('/', (req, res) => {
    try {
      res.json({ ok: true, ...knowledgeStore.create(db, req.body || {}) });
    } catch (e) {
      res.status(400).json({ error: String(e?.message || e) });
    }
  });

  router.put('/:id', (req, res) => {
    try {
      knowledgeStore.update(db, Number(req.params.id), req.body || {});
      res.json({ ok: true });
    } catch (e) {
      res.status(400).json({ error: String(e?.message || e) });
    }
  });

  router.delete('/:id', (req, res) => {
    knowledgeStore.delete(db, Number(req.params.id));
    res.json({ ok: true });
  });

  return router;
}

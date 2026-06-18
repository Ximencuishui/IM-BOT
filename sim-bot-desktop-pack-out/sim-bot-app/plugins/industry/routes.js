import express from 'express';
import { industryStore } from './store.js';

export function createRouter(ctx) {
  const router = express.Router();
  const { db } = ctx;

  // ==================== 店铺信息 ====================

  router.get('/info', (req, res) => {
    res.json(industryStore.getShopInfo(db) || {});
  });

  router.put('/info', (req, res) => {
    try {
      industryStore.upsertShopInfo(db, req.body || {});
      res.json({ ok: true });
    } catch (e) {
      res.status(400).json({ error: String(e?.message || e) });
    }
  });

  // ==================== 服务项目 ====================

  router.get('/services', (req, res) => {
    const { category, is_active, page, pageSize } = req.query;
    res.json(industryStore.listServices(db, {
      category,
      is_active: is_active !== undefined ? is_active === 'true' || is_active === '1' : undefined,
      page: Number(page) || 1,
      pageSize: Number(pageSize) || 50,
    }));
  });

  router.get('/services/:id', (req, res) => {
    const svc = industryStore.getServiceById(db, Number(req.params.id));
    res.json(svc ? { service: svc } : { error: '服务不存在' });
  });

  router.post('/services', (req, res) => {
    try {
      res.json({ ok: true, ...industryStore.createService(db, req.body || {}) });
    } catch (e) {
      res.status(400).json({ error: String(e?.message || e) });
    }
  });

  router.put('/services/:id', (req, res) => {
    try {
      industryStore.updateService(db, Number(req.params.id), req.body || {});
      res.json({ ok: true });
    } catch (e) {
      res.status(400).json({ error: String(e?.message || e) });
    }
  });

  router.delete('/services/:id', (req, res) => {
    industryStore.deleteService(db, Number(req.params.id));
    res.json({ ok: true });
  });

  // ==================== 待回答问题 ====================

  router.get('/pending-questions', (req, res) => {
    const { status, page, pageSize } = req.query;
    res.json(industryStore.listPendingQuestions(db, {
      status: status || 'pending',
      page: Number(page) || 1,
      pageSize: Number(pageSize) || 20,
    }));
  });

  router.post('/pending-questions', (req, res) => {
    try {
      res.json({ ok: true, ...industryStore.createPendingQuestion(db, req.body || {}) });
    } catch (e) {
      res.status(400).json({ error: String(e?.message || e) });
    }
  });

  router.post('/pending-questions/:id/answer', (req, res) => {
    try {
      res.json(industryStore.answerPendingQuestion(db, Number(req.params.id), req.body?.answer));
    } catch (e) {
      res.status(400).json({ error: String(e?.message || e) });
    }
  });

  return router;
}
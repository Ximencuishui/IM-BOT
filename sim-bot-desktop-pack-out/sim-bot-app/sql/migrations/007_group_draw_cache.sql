-- PRD 5.2：开奖后缓存，供「总结」指令回放财务审计
CREATE TABLE IF NOT EXISTS group_draw_cache (
  wx_group_id TEXT PRIMARY KEY,
  draw_batch_id TEXT NOT NULL,
  guide_word TEXT NOT NULL,
  ball_txt TEXT,
  te_ma_only INTEGER DEFAULT 0,
  scopes_json TEXT NOT NULL,
  hit_details_json TEXT NOT NULL,
  created_at TEXT DEFAULT (datetime('now'))
);

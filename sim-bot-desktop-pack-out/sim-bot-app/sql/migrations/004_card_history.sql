-- PRD: 卡密使用历史
CREATE TABLE IF NOT EXISTS card_history (
  card_no TEXT PRIMARY KEY,
  used_at TEXT NOT NULL,
  target_id TEXT NOT NULL
);

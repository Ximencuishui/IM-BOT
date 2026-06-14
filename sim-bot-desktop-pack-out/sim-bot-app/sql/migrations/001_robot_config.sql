-- PRD: 机器人自身授权
CREATE TABLE IF NOT EXISTS robot_config (
  wxid TEXT PRIMARY KEY,
  expire_date TEXT NOT NULL,
  last_card_cipher TEXT,
  integrity_hash TEXT NOT NULL
);

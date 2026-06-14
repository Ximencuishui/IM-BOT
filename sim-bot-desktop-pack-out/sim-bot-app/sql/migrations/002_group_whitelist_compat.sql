-- PRD: 白名单群（与 wx_groups 双写兼容）
CREATE TABLE IF NOT EXISTS group_whitelist (
  group_id TEXT PRIMARY KEY,
  group_name TEXT,
  owner_wxid TEXT,
  member_count INTEGER DEFAULT 0,
  expire_datetime TEXT NOT NULL,
  last_card_cipher TEXT,
  integrity_hash TEXT NOT NULL DEFAULT ''
);

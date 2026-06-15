-- 批量口语：每组、平特二连/平特尾、句首「新」渠道 shorthand
INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word) VALUES
  ('AMOUNT', '各', '每组'),
  ('PLAY', '连肖', '平特二连'),
  ('PLAY', '连肖', '平特二连肖'),
  ('PLAY', '平尾', '平特尾');

INSERT OR IGNORE INTO cmd_algo_aliases (alias_word, maps_to, is_active, updated_at)
VALUES ('每组', '各', 1, datetime('now'));

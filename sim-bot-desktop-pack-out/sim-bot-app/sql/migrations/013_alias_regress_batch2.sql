-- 回归批次：渠道/玩法口语（引擎预处理的项勿写入，见 016）
INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word) VALUES
  ('REGION', '新澳门', '新奥'),
  ('REGION', '香港', '港'),
  ('REGION', '香港', '香'),
  ('PLAY', '连码', '三中三'),
  ('PLAY', '连码', '二中二'),
  ('PLAY', '连码', '五不中');

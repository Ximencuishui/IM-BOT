-- chinese_amount.js 原内置尾缀单位并入 alias_config SET（标准词：元）
INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word) VALUES
  ('SET', '元', '元'),
  ('SET', '元', '块'),
  ('SET', '元', '整'),
  ('SET', '元', '角'),
  ('SET', '元', '分'),
  ('SET', '元', '米'),
  ('SET', '元', '蒙'),
  ('SET', '元', 'A'),
  ('SET', '元', 'a'),
  ('SET', '元', '斤');

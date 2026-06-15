-- PRD 6.2 默认别名种子（各词段 / 金额单位 / 地区）
INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word) VALUES
  ('AMOUNT', '各', '各数'),
  ('AMOUNT', '各', '个数'),
  ('AMOUNT', '各', '个'),
  ('AMOUNT', '各', '各组'),
  ('AMOUNT', '各', '每个'),
  ('SET', '元', '米'),
  ('SET', '元', '闷'),
  ('SET', '元', '焖'),
  ('SET', '元', '蒙'),
  ('SET', '元', 'A'),
  ('SET', '元', 'a'),
  ('REGION', '新澳门', '新奥'),
  ('REGION', '新澳门', '奥'),
  ('REGION', '老澳门', '老奥');

-- 金额段合计标记（各+单注金额 后的 = / 共 / 统共 / 一共 / 合计 / 合 + 数字）
INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word) VALUES
  ('SEGMENT_TOTAL', '=', '='),
  ('SEGMENT_TOTAL', '=', '共'),
  ('SEGMENT_TOTAL', '=', '统共'),
  ('SEGMENT_TOTAL', '=', '一共'),
  ('SEGMENT_TOTAL', '=', '合计'),
  ('SEGMENT_TOTAL', '=', '合');

INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word) VALUES
  ('PLAY', '三连肖', '三友'),
  ('PLAY', '三连肖', '三有'),
  ('PLAY', '四连肖', '四有'),
  ('PLAY', '四连肖', '四友'),
  ('PLAY', '四连肖', '平特四连肖'),
  ('PLAY', '四连肖', '平特四连');

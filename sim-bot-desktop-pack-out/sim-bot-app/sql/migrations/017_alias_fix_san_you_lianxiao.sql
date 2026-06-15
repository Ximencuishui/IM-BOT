-- 三有/三友 → 三连肖；四有/四友 → 四连肖；删除错误的「三四*」玩法别名（引擎仍可按句式展开三四复式）

UPDATE cmd_keyword_synonyms
SET canonical_word = '三连肖', is_active = 1, updated_at = datetime('now')
WHERE scope = 'category_word' AND alias_word IN ('三友', '三有');

UPDATE alias_config
SET standard_word = '三连肖'
WHERE category = 'PLAY' AND alias_word IN ('三友', '三有');

DELETE FROM alias_config
WHERE category = 'PLAY' AND alias_word IN ('三四有', '三四友', '三四连肖');

DELETE FROM cmd_keyword_synonyms
WHERE scope = 'category_word' AND alias_word IN ('三四有', '三四友', '三四连肖');

INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word) VALUES
  ('PLAY', '三连肖', '三友'),
  ('PLAY', '三连肖', '三有'),
  ('PLAY', '四连肖', '四友'),
  ('PLAY', '四连肖', '四有');

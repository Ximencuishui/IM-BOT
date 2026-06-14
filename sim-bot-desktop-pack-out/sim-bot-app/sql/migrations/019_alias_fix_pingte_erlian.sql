-- 平特二连为独立玩法（《玩法说明》），不应作为连肖别名（012 误配）

DELETE FROM alias_config
WHERE category = 'PLAY'
  AND alias_word IN ('平特二连', '平特二连肖')
  AND standard_word = '连肖';

DELETE FROM cmd_keyword_synonyms
WHERE scope = 'category_word'
  AND alias_word IN ('平特二连', '平特二连肖')
  AND canonical_word = '连肖';

INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word) VALUES
  ('PLAY', '平特二连', '平特二连'),
  ('PLAY', '平特二连', '平特二连肖');

UPDATE alias_config
SET standard_word = '平特二连'
WHERE category = 'PLAY'
  AND alias_word IN ('平特二连', '平特二连肖');

INSERT OR IGNORE INTO cmd_keyword_synonyms (scope, canonical_word, alias_word, is_active, updated_at)
VALUES
  ('category_word', '平特二连', '平特二连', 1, datetime('now')),
  ('category_word', '平特二连', '平特二连肖', 1, datetime('now'));

UPDATE cmd_keyword_synonyms
SET canonical_word = '平特二连', is_active = 1, updated_at = datetime('now')
WHERE scope = 'category_word'
  AND alias_word IN ('平特二连', '平特二连肖');

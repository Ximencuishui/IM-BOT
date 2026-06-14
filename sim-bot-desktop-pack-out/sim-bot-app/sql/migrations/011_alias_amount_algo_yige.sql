-- 算法词「各」别名：口语「一个」（如 牛羊马一个10）
INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word)
VALUES ('AMOUNT', '各', '一个');

INSERT OR IGNORE INTO cmd_algo_aliases (alias_word, maps_to, is_active, updated_at)
VALUES ('一个', '各', 1, datetime('now'));

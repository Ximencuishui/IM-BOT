-- 旧 cmd_keyword_synonyms / cmd_algo_aliases 一次性迁入 alias_config（幂等）
INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word)
SELECT 'REGION', canonical_word, alias_word FROM cmd_keyword_synonyms
WHERE scope = 'guide_word' AND is_active = 1
  AND TRIM(alias_word) <> '' AND TRIM(canonical_word) <> '';

INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word)
SELECT 'PLAY', canonical_word, alias_word FROM cmd_keyword_synonyms
WHERE scope = 'category_word' AND is_active = 1
  AND TRIM(alias_word) <> '' AND TRIM(canonical_word) <> '';

INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word)
SELECT 'SET', canonical_word, alias_word FROM cmd_keyword_synonyms
WHERE scope = 'amount_unit' AND is_active = 1
  AND TRIM(alias_word) <> '' AND TRIM(canonical_word) <> '';

INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word)
SELECT 'INSTRUCTION', canonical_word, alias_word FROM cmd_keyword_synonyms
WHERE scope = 'instruction' AND is_active = 1
  AND TRIM(alias_word) <> '' AND TRIM(canonical_word) <> '';

INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word)
SELECT 'AMOUNT', maps_to, alias_word FROM cmd_algo_aliases
WHERE is_active = 1 AND TRIM(alias_word) <> '' AND TRIM(maps_to) <> '';

INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word)
SELECT 'AMOUNT', canonical_word, alias_word FROM cmd_keyword_synonyms
WHERE scope = 'algo' AND is_active = 1
  AND TRIM(alias_word) <> '' AND TRIM(canonical_word) <> '';

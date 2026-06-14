-- 清理误分类别名：引擎预处理项、各+阿拉伯数字等（幂等，每次启动可执行）

DELETE FROM alias_config
WHERE category = 'AMOUNT'
  AND standard_word = '各'
  AND alias_word GLOB '各[0-9]*';

DELETE FROM cmd_algo_aliases
WHERE maps_to = '各'
  AND alias_word GLOB '各[0-9]*';

DELETE FROM alias_config
WHERE category = 'REGION'
  AND standard_word = '新澳门'
  AND alias_word IN ('新奥特', '噢待码', '待码');

DELETE FROM cmd_keyword_synonyms
WHERE scope = 'guide_word'
  AND canonical_word = '新澳门'
  AND alias_word IN ('新奥特', '噢待码', '待码');

DELETE FROM alias_config
WHERE category = 'PLAY'
  AND standard_word = '平特'
  AND alias_word IN (
    '鼠平', '牛平', '虎平', '兔平', '龙平', '蛇平', '马平', '羊平',
    '猴平', '鸡平', '狗平', '猪平'
  );

DELETE FROM cmd_keyword_synonyms
WHERE scope = 'category_word'
  AND canonical_word = '平特'
  AND alias_word IN (
    '鼠平', '牛平', '虎平', '兔平', '龙平', '蛇平', '马平', '羊平',
    '猴平', '鸡平', '狗平', '猪平'
  );

-- 「各五」「各三十五」「各百」等为「各+内嵌中文金额」，由引擎 expandChineseAmountAfterEachKeyword 处理，
-- 不是算法词「各」的同义词；从 alias_config / cmd_algo_aliases 中清理误入库项。

DELETE FROM alias_config
WHERE category = 'AMOUNT'
  AND standard_word = '各'
  AND alias_word GLOB '各*'
  AND alias_word NOT IN (
    '各',
    '各数',
    '各位',
    '各个',
    '各位数',
    '各号',
    '个数',
    '每号',
    '每各',
    '个个',
    '各组',
    '每个号',
    '一个'
  );

DELETE FROM cmd_algo_aliases
WHERE maps_to = '各'
  AND alias_word GLOB '各*'
  AND alias_word NOT IN (
    '各',
    '各数',
    '各位',
    '各个',
    '各位数',
    '各号',
    '个数',
    '每号',
    '每各',
    '个个',
    '各组',
    '每个号',
    '一个'
  );

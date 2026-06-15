-- PRD 指令类别名种子（同步至 cmd_keyword_synonyms scope=instruction）
INSERT OR IGNORE INTO alias_config (category, standard_word, alias_word) VALUES
  ('INSTRUCTION', 'help', '帮助'),
  ('INSTRUCTION', 'clear_order', '清零'),
  ('INSTRUCTION', 'group_report', '报表'),
  ('INSTRUCTION', 'settlement_summary', '总结');

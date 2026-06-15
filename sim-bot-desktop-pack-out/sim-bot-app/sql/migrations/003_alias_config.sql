-- PRD: 动态别名
CREATE TABLE IF NOT EXISTS alias_config (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  category TEXT NOT NULL,
  standard_word TEXT NOT NULL,
  alias_word TEXT NOT NULL UNIQUE
);

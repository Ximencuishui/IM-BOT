-- 桌面端机器人运行与 SimBot 风格主程序授权（对齐 sim-bot-node）

CREATE TABLE IF NOT EXISTS t_desktop_robot_config (
    wxid VARCHAR(128) PRIMARY KEY,
    expire_date CHAR(8) NOT NULL COMMENT 'YYYYMMDD',
    last_card_cipher TEXT,
    integrity_hash VARCHAR(64) NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS t_app_settings (
    setting_key VARCHAR(128) PRIMARY KEY,
    setting_value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS t_bot_work_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    level VARCHAR(16) NOT NULL DEFAULT 'info',
    message VARCHAR(2000) NOT NULL,
    detail_json TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS t_card_history (
    card_no VARCHAR(64) PRIMARY KEY,
    target_id VARCHAR(128) NOT NULL,
    used_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_bot_work_logs_created ON t_bot_work_logs(created_at DESC);

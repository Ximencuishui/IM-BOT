-- 桌面端多群配置（对齐 sim-bot-node wx_groups / wx_chatroom_cache）

CREATE TABLE IF NOT EXISTS t_wx_groups (
    wx_group_id VARCHAR(128) PRIMARY KEY,
    name VARCHAR(255),
    manual_owner VARCHAR(128),
    group_admin_user_id INTEGER,
    expires_at DATETIME,
    last_card_cipher TEXT,
    integrity_hash VARCHAR(64),
    is_active TINYINT DEFAULT 1,
    strict_play_routes TINYINT DEFAULT 0,
    customer_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS t_wx_chatroom_cache (
    room_id VARCHAR(128) PRIMARY KEY,
    nick_name VARCHAR(255),
    remark VARCHAR(255),
    member_count INTEGER DEFAULT 0,
    owner_wxid VARCHAR(128),
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_wx_groups_active ON t_wx_groups(is_active);
CREATE INDEX IF NOT EXISTS idx_wx_groups_expires ON t_wx_groups(expires_at);

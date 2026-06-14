-- 迁移脚本: 添加机器人交互相关表
-- 创建时间: 2026-04-15

-- 1. 创建指令配置表
CREATE TABLE IF NOT EXISTS t_command_config (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '指令ID',
    command_name VARCHAR(50) NOT NULL UNIQUE COMMENT '指令名称',
    keywords TEXT COMMENT '关键词列表(JSON)',
    patterns TEXT COMMENT '正则表达式列表(JSON)',
    response_template TEXT COMMENT '回复模板',
    description VARCHAR(255) COMMENT '指令描述',
    is_active TINYINT DEFAULT 1 COMMENT '是否启用',
    usage_count INT DEFAULT 0 COMMENT '使用次数统计',
    created_at DATETIME DEFAULT NOW() COMMENT '创建时间',
    updated_at DATETIME DEFAULT NOW() ON UPDATE NOW() COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='指令配置表';

-- 2. 创建报表推送日志表
CREATE TABLE IF NOT EXISTS t_report_push_log (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '日志ID',
    route_id INT COMMENT '配送线路ID',
    push_time DATETIME NOT NULL COMMENT '推送时间',
    recipient_group VARCHAR(64) COMMENT '接收群ID',
    report_content TEXT COMMENT '推送内容',
    status VARCHAR(20) DEFAULT 'success' COMMENT '推送状态: success/failed',
    error_message TEXT COMMENT '错误信息',
    created_at DATETIME DEFAULT NOW() COMMENT '创建时间',

    INDEX idx_route_push_time (route_id, push_time),
    FOREIGN KEY (route_id) REFERENCES t_delivery_route(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='报表推送日志表';

-- 3. 插入默认指令配置
INSERT INTO t_command_config (command_name, keywords, patterns, response_template, description, is_active) VALUES
('sales_report',
 '["报表", "统计", "汇总", "今日报表", "销售统计"]',
 '["(?:报表|统计|汇总)", "(?:今日|今天).*(?:报表|统计)", "(?:配送|订单).*(?:多少|统计)"]',
 'sales_report',
 '销售员查询负责线路的订单汇总',
 1),

('customer_query',
 '["查订单", "查询", "多少钱", "我的订单", "查货"]',
 '["(?:查|查询).*(?:订单|货)", "(?:多少|什么价格|多少钱)", "(?:我的|本人).*(?:订单|货)"]',
 'customer_query',
 '客户查询当日订单详情',
 1),

('help',
 '["帮助", "help", "指令", "怎么用"]',
 '["(?:帮助|help|指令|怎么用)"]',
 'help_text',
 '显示帮助信息',
 1)
ON DUPLICATE KEY UPDATE description = VALUES(description);

-- 本地化配送服务商智能订货统计工具 - 数据库初始化脚本
-- MySQL 8.0+

-- 创建数据库
CREATE DATABASE IF NOT EXISTS food_delivery DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE food_delivery;

-- =============================================
-- 1. 配送线路表
-- =============================================
CREATE TABLE t_delivery_route (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '线路ID',
    route_name VARCHAR(100) NOT NULL COMMENT '线路名称',
    route_code VARCHAR(50) UNIQUE COMMENT '线路编码',
    description VARCHAR(255) COMMENT '线路描述',
    is_active TINYINT DEFAULT 1 COMMENT '是否启用: 1-启用, 0-禁用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_route_code (route_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='配送线路表';

-- =============================================
-- 2. 商品表
-- =============================================
CREATE TABLE t_product (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '商品ID',
    product_name VARCHAR(100) NOT NULL COMMENT '商品名称',
    product_code VARCHAR(50) COMMENT '商品编码',
    shortcut_codes VARCHAR(255) COMMENT '快捷码列表,逗号分隔,如: TD,土,土豆',
    unit VARCHAR(20) DEFAULT '斤' COMMENT '默认单位: 斤/两/箱/包/个',
    price DECIMAL(10, 2) DEFAULT 0.00 COMMENT '参考单价(元)',
    category VARCHAR(50) COMMENT '商品分类: 蔬菜/肉类/调料/其他',
    attributes JSON COMMENT '商品属性JSON数组,最多10个属性,如: [{"name":"颜色","value":"红色"},{"name":"尺码","value":"L"}]',
    commission DECIMAL(10, 2) DEFAULT 0.00 COMMENT '佣金(元)',
    points INT DEFAULT 0 COMMENT '积分',
    is_active TINYINT DEFAULT 1 COMMENT '是否启用: 1-启用, 0-禁用',
    sort_order INT DEFAULT 0 COMMENT '排序权重',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_product_name (product_name),
    INDEX idx_product_code (product_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='商品表';

-- =============================================
-- 3. 客户表
-- =============================================
CREATE TABLE t_user (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '客户ID',
    customer_name VARCHAR(100) NOT NULL COMMENT '客户姓名/店铺名',
    phone VARCHAR(20) COMMENT '联系电话',
    address VARCHAR(255) COMMENT '配送地址',
    wx_group_id VARCHAR(64) COMMENT '微信群ID',
    wx_alias VARCHAR(64) COMMENT '微信昵称',
    route_id BIGINT COMMENT '所属配送线路ID',
    sales_person VARCHAR(50) COMMENT '负责销售',
    is_active TINYINT DEFAULT 1 COMMENT '是否启用: 1-启用, 0-禁用',
    remark VARCHAR(255) COMMENT '备注信息',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_wx_group_id (wx_group_id),
    INDEX idx_route_id (route_id),
    INDEX idx_sales_person (sales_person),
    FOREIGN KEY (route_id) REFERENCES t_delivery_route(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='客户表';

-- =============================================
-- 4. 订单表
-- =============================================
CREATE TABLE t_order (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '订单ID',
    order_uuid VARCHAR(64) UNIQUE NOT NULL COMMENT '订单唯一标识(用于幂等性)',
    customer_id BIGINT NOT NULL COMMENT '客户ID',
    order_date DATE NOT NULL COMMENT '订单日期',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '订单状态: pending-待确认, confirmed-已确认, completed-已完成, cancelled-已取消',
    total_amount DECIMAL(10, 2) DEFAULT 0.00 COMMENT '订单总金额',
    remark VARCHAR(500) COMMENT '订单备注',
    source_type VARCHAR(20) DEFAULT 'wechat' COMMENT '订单来源: wechat-微信群, manual-手工录入, api-API导入',
    confirmed_by VARCHAR(50) COMMENT '确认人(销售)',
    confirmed_at DATETIME COMMENT '确认时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_order_uuid (order_uuid),
    INDEX idx_customer_id (customer_id),
    INDEX idx_order_date (order_date),
    INDEX idx_status (status),
    FOREIGN KEY (customer_id) REFERENCES t_user(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单表';

-- =============================================
-- 5. 订单明细表
-- =============================================
CREATE TABLE t_order_item (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '明细ID',
    order_id BIGINT NOT NULL COMMENT '订单ID',
    product_id BIGINT NOT NULL COMMENT '商品ID',
    product_name VARCHAR(100) COMMENT '商品名称快照',
    quantity DECIMAL(10, 2) NOT NULL COMMENT '数量',
    unit VARCHAR(20) DEFAULT '斤' COMMENT '单位',
    unit_price DECIMAL(10, 2) DEFAULT 0.00 COMMENT '单价',
    subtotal DECIMAL(10, 2) DEFAULT 0.00 COMMENT '小计金额',
    remark VARCHAR(255) COMMENT '商品备注,如: 要嫩的/不要葱',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_order_id (order_id),
    INDEX idx_product_id (product_id),
    FOREIGN KEY (order_id) REFERENCES t_order(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES t_product(id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单明细表';

-- =============================================
-- 6. 原始消息记录表
-- =============================================
CREATE TABLE t_raw_message (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '消息ID',
    group_id VARCHAR(64) COMMENT '微信群ID',
    sender VARCHAR(64) COMMENT '发送者昵称',
    content TEXT COMMENT '消息内容',
    raw_json TEXT COMMENT '原始JSON数据',
    message_hash VARCHAR(64) COMMENT '消息指纹(MD5)',
    received_at DATETIME COMMENT '接收时间',
    processed TINYINT DEFAULT 0 COMMENT '是否已处理: 0-未处理, 1-已处理, 2-处理失败',
    parse_result TEXT COMMENT '解析结果JSON',
    confidence_score DECIMAL(3, 2) COMMENT '解析置信度(0-1)',
    error_message TEXT COMMENT '错误信息',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_group_id (group_id),
    INDEX idx_received_at (received_at),
    INDEX idx_processed (processed),
    INDEX idx_message_hash (message_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='原始消息记录表';

-- =============================================
-- 7. 系统配置表
-- =============================================
CREATE TABLE t_system_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '配置ID',
    config_key VARCHAR(100) UNIQUE NOT NULL COMMENT '配置键',
    config_value TEXT COMMENT '配置值',
    description VARCHAR(255) COMMENT '配置描述',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统配置表';

-- =============================================
-- 初始化基础数据
-- =============================================

-- 插入示例配送线路
INSERT INTO t_delivery_route (route_name, route_code, description) VALUES
('一号线', 'route_001', '城东片区'),
('二号线', 'route_002', '城西片区'),
('三号线', 'route_003', '城南片区');

-- 插入示例商品
INSERT INTO t_product (product_name, product_code, shortcut_codes, unit, price, category) VALUES
('土豆', 'PROD_001', 'TD,土,土豆', '斤', 2.50, '蔬菜'),
('猪肉', 'PROD_002', 'R,肉,猪肉', '斤', 15.00, '肉类'),
('白菜', 'PROD_003', 'BC,白菜', '斤', 1.20, '蔬菜'),
('鸡蛋', 'PROD_004', 'JD,蛋,鸡蛋', '斤', 6.50, '其他'),
('青椒', 'PROD_005', 'QJ,椒,青椒', '斤', 3.80, '蔬菜');

-- 插入系统配置
INSERT INTO t_system_config (config_key, config_value, description) VALUES
('cutoff_time', '21:30', '每日截单时间'),
('parse_confidence_threshold', '0.7', '订单解析置信度阈值'),
('message_dedup_ttl', '86400', '消息去重TTL(秒)');

-- =============================================
-- 用户端系统表（v2.0新增）
-- =============================================

-- 8. 用户账户表
CREATE TABLE t_user_account (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '用户ID',
    email VARCHAR(100) UNIQUE NOT NULL COMMENT '登录邮箱',
    password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希',
    username VARCHAR(50) COMMENT '用户名/昵称',
    phone VARCHAR(20) COMMENT '联系电话',
    company_name VARCHAR(100) COMMENT '公司/店铺名称',
    subscription_type VARCHAR(20) DEFAULT 'monthly' COMMENT '订阅类型: monthly-月付, yearly-年付',
    subscription_expires_at DATETIME COMMENT '订阅过期时间',
    max_groups INT DEFAULT 3 COMMENT '最大允许群数量',
    is_active TINYINT DEFAULT 1 COMMENT '账户是否激活',
    last_login_at DATETIME COMMENT '最后登录时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_email (email),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户账户表';

-- 9. 授权码表(v2)
CREATE TABLE t_license_v2 (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '授权ID',
    user_id BIGINT NOT NULL COMMENT '所属用户ID',
    license_code VARCHAR(64) UNIQUE NOT NULL COMMENT '授权码',
    license_type VARCHAR(20) DEFAULT 'monthly' COMMENT '授权类型: monthly-月付, yearly-年付',
    bound_to VARCHAR(100) COMMENT '绑定的微信群ID',
    assigned_to BIGINT COMMENT '分配给的销售员ID',
    machine_id VARCHAR(64) COMMENT '机器指纹',
    activated_at DATETIME COMMENT '激活时间',
    expires_at DATETIME COMMENT '过期时间',
    is_active TINYINT DEFAULT 0 COMMENT '是否激活',
    is_revoked TINYINT DEFAULT 0 COMMENT '是否已撤销',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_license_code (license_code),
    INDEX idx_user_id (user_id),
    INDEX idx_assigned_to (assigned_to),
    FOREIGN KEY (user_id) REFERENCES t_user_account(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='授权码表v2';

-- 10. 团队成员表
CREATE TABLE t_team_member (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '成员ID',
    user_id BIGINT NOT NULL COMMENT '所属用户ID',
    name VARCHAR(50) NOT NULL COMMENT '销售员姓名',
    phone VARCHAR(20) COMMENT '联系电话',
    wx_id VARCHAR(64) COMMENT '微信号',
    managed_group_id VARCHAR(100) COMMENT '管理的微信群ID',
    position VARCHAR(50) COMMENT '职位',
    is_active TINYINT DEFAULT 1 COMMENT '是否在职',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_user_id (user_id),
    FOREIGN KEY (user_id) REFERENCES t_user_account(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='团队成员表';

-- 添加外键约束到t_license_v2
ALTER TABLE t_license_v2 ADD CONSTRAINT fk_license_team_member FOREIGN KEY (assigned_to) REFERENCES t_team_member(id) ON DELETE SET NULL;

-- 11. 机器人配置表
CREATE TABLE t_robot_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '配置ID',
    user_id BIGINT NOT NULL COMMENT '所属用户ID',
    config_name VARCHAR(50) DEFAULT '默认机器人' COMMENT '配置名称',
    wechat_path VARCHAR(255) COMMENT '微信安装路径',
    wechat_version VARCHAR(20) COMMENT '微信版本号',
    hook_dll_path VARCHAR(255) COMMENT 'Hook DLL路径',
    tcp_server_host VARCHAR(50) DEFAULT '127.0.0.1' COMMENT 'TCP服务器地址',
    tcp_server_port INT DEFAULT 8888 COMMENT 'TCP服务器端口',
    auto_start TINYINT DEFAULT 0 COMMENT '是否自动启动',
    is_default TINYINT DEFAULT 0 COMMENT '是否为默认配置',
    status VARCHAR(20) DEFAULT 'stopped' COMMENT '运行状态: stopped-停止, running-运行中, error-错误',
    last_started_at DATETIME COMMENT '最后启动时间',
    last_error TEXT COMMENT '最后错误信息',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_user_id (user_id),
    FOREIGN KEY (user_id) REFERENCES t_user_account(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='机器人配置表';

-- 12. 自动回复规则表
CREATE TABLE t_reply_rule (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '规则ID',
    robot_config_id BIGINT NOT NULL COMMENT '所属机器人配置ID',
    rule_name VARCHAR(50) NOT NULL COMMENT '规则名称',
    trigger_type VARCHAR(20) DEFAULT 'keyword' COMMENT '触发类型: keyword-关键词, pattern-正则表达式, all-所有消息',
    trigger_content TEXT COMMENT '触发内容(关键词或正则)',
    reply_type VARCHAR(20) DEFAULT 'text' COMMENT '回复类型: text-文本, template-模板',
    reply_content TEXT NOT NULL COMMENT '回复内容',
    priority INT DEFAULT 0 COMMENT '优先级(数字越大优先级越高)',
    is_active TINYINT DEFAULT 1 COMMENT '是否启用',
    match_count INT DEFAULT 0 COMMENT '匹配次数统计',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_robot_config_id (robot_config_id),
    FOREIGN KEY (robot_config_id) REFERENCES t_robot_config(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='自动回复规则表';

-- 13. 消息解析规则表
CREATE TABLE t_parse_rule (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '规则ID',
    user_id BIGINT NOT NULL COMMENT '所属用户ID',
    rule_name VARCHAR(50) NOT NULL COMMENT '规则名称',
    rule_type VARCHAR(20) DEFAULT 'regex' COMMENT '规则类型: regex-正则, keyword-关键词, custom-自定义脚本',
    pattern TEXT COMMENT '匹配模式(正则表达式或关键词)',
    extract_fields TEXT COMMENT '提取字段配置JSON',
    priority INT DEFAULT 0 COMMENT '优先级',
    is_active TINYINT DEFAULT 1 COMMENT '是否启用',
    description VARCHAR(255) COMMENT '规则描述',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_user_id (user_id),
    FOREIGN KEY (user_id) REFERENCES t_user_account(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='消息解析规则表';

-- 14. 统计规则表
CREATE TABLE t_stat_rule (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '规则ID',
    user_id BIGINT NOT NULL COMMENT '所属用户ID',
    rule_name VARCHAR(50) NOT NULL COMMENT '规则名称',
    stat_type VARCHAR(20) DEFAULT 'daily' COMMENT '统计类型: daily-日报, weekly-周报, monthly-月报, custom-自定义',
    dimensions TEXT COMMENT '统计维度JSON: 按商品/按客户/按线路等',
    filters TEXT COMMENT '过滤条件JSON',
    chart_type VARCHAR(20) DEFAULT 'bar' COMMENT '图表类型: bar-柱状图, line-折线图, pie-饼图',
    refresh_interval INT DEFAULT 3600 COMMENT '刷新间隔(秒)',
    is_active TINYINT DEFAULT 1 COMMENT '是否启用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_user_id (user_id),
    FOREIGN KEY (user_id) REFERENCES t_user_account(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='统计规则表';

-- 15. 看板组件配置表
CREATE TABLE t_dashboard_widget (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '组件ID',
    user_id BIGINT NOT NULL COMMENT '所属用户ID',
    widget_name VARCHAR(50) NOT NULL COMMENT '组件名称',
    widget_type VARCHAR(20) DEFAULT 'stat_card' COMMENT '组件类型: stat_card-统计卡片, chart-图表, table-表格',
    data_source TEXT COMMENT '数据源配置JSON',
    stat_period VARCHAR(20) DEFAULT 'today' COMMENT '统计周期: today-今日, week-本周, month-本月, custom-自定义',
    position_x INT DEFAULT 0 COMMENT 'X坐标位置',
    position_y INT DEFAULT 0 COMMENT 'Y坐标位置',
    width INT DEFAULT 1 COMMENT '宽度(栅格单位)',
    height INT DEFAULT 1 COMMENT '高度(栅格单位)',
    is_visible TINYINT DEFAULT 1 COMMENT '是否显示',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_user_id (user_id),
    FOREIGN KEY (user_id) REFERENCES t_user_account(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='看板组件配置表';

-- 16. 规则模板库表
CREATE TABLE t_rule_template (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '模板ID',
    template_name VARCHAR(100) NOT NULL COMMENT '模板名称',
    industry VARCHAR(50) NOT NULL COMMENT '所属行业',
    description VARCHAR(500) COMMENT '模板描述',
    parse_rules TEXT COMMENT '解析规则JSON数组',
    stat_rules TEXT COMMENT '统计规则JSON数组',
    reply_rules TEXT COMMENT '回复规则JSON数组',
    source_type VARCHAR(20) DEFAULT 'official' COMMENT '来源: official-官方, community-社区, user-用户上传',
    author_id BIGINT COMMENT '上传用户ID',
    version VARCHAR(20) DEFAULT '1.0' COMMENT '版本号',
    download_count INT DEFAULT 0 COMMENT '下载次数',
    rating DECIMAL(3, 2) DEFAULT 0.00 COMMENT '评分(0-5)',
    rating_count INT DEFAULT 0 COMMENT '评分人数',
    is_public TINYINT DEFAULT 1 COMMENT '是否公开',
    is_featured TINYINT DEFAULT 0 COMMENT '是否精选',
    is_active TINYINT DEFAULT 1 COMMENT '是否启用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_industry (industry),
    INDEX idx_source_type (source_type),
    FOREIGN KEY (author_id) REFERENCES t_user_account(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='规则模板库表';

-- 17. 用户规则备份表
CREATE TABLE t_user_rule_backup (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '备份ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    backup_name VARCHAR(100) COMMENT '备份名称',
    parse_rules TEXT COMMENT '解析规则JSON',
    stat_rules TEXT COMMENT '统计规则JSON',
    reply_rules TEXT COMMENT '回复规则JSON',
    template_id BIGINT COMMENT '来源模板ID',
    version VARCHAR(20) DEFAULT '1.0' COMMENT '版本号',
    is_current TINYINT DEFAULT 1 COMMENT '是否为当前使用版本',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_user_id (user_id),
    INDEX idx_template_id (template_id),
    FOREIGN KEY (user_id) REFERENCES t_user_account(id) ON DELETE CASCADE,
    FOREIGN KEY (template_id) REFERENCES t_rule_template(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户规则备份表';

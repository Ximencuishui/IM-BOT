-- 迁移脚本: 歌曲分离工作室插件数据库表
-- 创建时间: 2026-06-15

-- =============================================
-- 1. 服务类型与定价配置表
-- =============================================
CREATE TABLE IF NOT EXISTS t_studio_service_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '配置ID',
    service_name VARCHAR(50) NOT NULL COMMENT '服务名称',
    service_code VARCHAR(30) UNIQUE NOT NULL COMMENT '服务编码',
    description VARCHAR(500) COMMENT '服务描述',
    base_price DECIMAL(10,2) DEFAULT 0.00 COMMENT '基础价格(元)',
    price_unit VARCHAR(20) DEFAULT '次' COMMENT '计价单位',
    is_active TINYINT DEFAULT 1 COMMENT '是否启用',
    sort_order INT DEFAULT 0 COMMENT '排序权重',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_service_code (service_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工作室服务配置表';

-- =============================================
-- 2. 订单表
-- =============================================
CREATE TABLE IF NOT EXISTS t_studio_order (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '订单ID',
    order_no VARCHAR(50) UNIQUE NOT NULL COMMENT '订单编号',
    service_code VARCHAR(30) NOT NULL COMMENT '服务编码',
    customer_wx_id VARCHAR(100) COMMENT '客户微信ID',
    customer_nickname VARCHAR(100) COMMENT '客户微信昵称',
    customer_phone VARCHAR(20) COMMENT '客户电话',
    source_type VARCHAR(20) DEFAULT 'group_chat' COMMENT '来源: group_chat/private_chat',
    source_group VARCHAR(100) COMMENT '来源群聊名称',
    requirement TEXT COMMENT '客户需求描述',
    song_name VARCHAR(200) COMMENT '歌曲名称',
    song_artist VARCHAR(200) COMMENT '歌手',
    song_link VARCHAR(500) COMMENT '歌曲链接',
    file_url VARCHAR(500) COMMENT '客户上传文件路径',
    file_name VARCHAR(200) COMMENT '原始文件名称',
    status VARCHAR(30) DEFAULT 'consulting' COMMENT '状态: consulting-咨询中, quoted-已报价, paid-已付款, processing-处理中, completed-已完成, cancelled-已取消',
    total_amount DECIMAL(10,2) DEFAULT 0.00 COMMENT '订单金额',
    paid_amount DECIMAL(10,2) DEFAULT 0.00 COMMENT '实付金额',
    result_file_url VARCHAR(500) COMMENT '结果文件路径',
    remark VARCHAR(500) COMMENT '备注',
    workflow_id VARCHAR(100) COMMENT '关联工作流ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_order_no (order_no),
    INDEX idx_customer_wx_id (customer_wx_id),
    INDEX idx_status (status),
    INDEX idx_service_code (service_code),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工作室订单表';

-- =============================================
-- 3. 工作流配置表
-- =============================================
CREATE TABLE IF NOT EXISTS t_studio_workflow_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '工作流ID',
    service_code VARCHAR(30) NOT NULL COMMENT '关联服务编码',
    workflow_name VARCHAR(100) NOT NULL COMMENT '工作流名称',
    workflow_type VARCHAR(30) DEFAULT 'auto' COMMENT '类型: auto-全自动, semi-auto-半自动, manual-手动',
    steps JSON COMMENT '工作流步骤定义JSON',
    script_path VARCHAR(255) COMMENT '脚本路径',
    is_active TINYINT DEFAULT 1 COMMENT '是否启用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_service_code (service_code),
    FOREIGN KEY (service_code) REFERENCES t_studio_service_config(service_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工作流配置表';

-- =============================================
-- 4. 工作流执行记录表
-- =============================================
CREATE TABLE IF NOT EXISTS t_studio_workflow_execution (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '执行ID',
    order_id BIGINT NOT NULL COMMENT '关联订单ID',
    workflow_id BIGINT NOT NULL COMMENT '关联工作流配置ID',
    execution_status VARCHAR(30) DEFAULT 'pending' COMMENT '状态: pending-待确认, running-执行中, completed-已完成, failed-失败',
    progress INT DEFAULT 0 COMMENT '进度百分比(0-100)',
    log TEXT COMMENT '执行日志',
    started_at DATETIME COMMENT '开始时间',
    completed_at DATETIME COMMENT '完成时间',
    error_message TEXT COMMENT '错误信息',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_order_id (order_id),
    FOREIGN KEY (order_id) REFERENCES t_studio_order(id),
    FOREIGN KEY (workflow_id) REFERENCES t_studio_workflow_config(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工作流执行记录表';

-- =============================================
-- 5. 知识库表
-- =============================================
CREATE TABLE IF NOT EXISTS t_studio_knowledge_base (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '条目ID',
    question VARCHAR(500) NOT NULL COMMENT '问题',
    answer TEXT COMMENT '答案',
    keywords JSON COMMENT '关键词数组',
    category VARCHAR(50) DEFAULT 'general' COMMENT '分类',
    source VARCHAR(20) DEFAULT 'auto' COMMENT '来源: auto-自动记录, manual-老板录入',
    is_resolved TINYINT DEFAULT 0 COMMENT '是否已解答',
    match_count INT DEFAULT 0 COMMENT '匹配次数',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_category (category),
    INDEX idx_is_resolved (is_resolved),
    FULLTEXT INDEX ft_question (question)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='知识库表';

-- =============================================
-- 6. 问候语配置表
-- =============================================
CREATE TABLE IF NOT EXISTS t_studio_greeting_config (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '配置ID',
    greeting_text TEXT NOT NULL COMMENT '问候内容',
    greeting_type VARCHAR(20) DEFAULT 'morning' COMMENT '类型: morning-早安, evening-晚安, holiday-节假日, custom-自定义',
    send_time TIME COMMENT '定时发送时间',
    target_groups JSON COMMENT '目标群聊ID数组',
    is_active TINYINT DEFAULT 1 COMMENT '是否启用',
    is_random TINYINT DEFAULT 0 COMMENT '是否随机选取',
    sort_order INT DEFAULT 0 COMMENT '排序权重',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_type (greeting_type),
    INDEX idx_send_time (send_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='问候语配置表';

-- =============================================
-- 7. 统计汇总表
-- =============================================
CREATE TABLE IF NOT EXISTS t_studio_statistics (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '统计ID',
    stat_date DATE NOT NULL COMMENT '统计日期',
    stat_type VARCHAR(20) DEFAULT 'daily' COMMENT '类型: daily-日报, weekly-周报, monthly-月报',
    service_code VARCHAR(30) COMMENT '服务编码(NULL表示总计)',
    order_count INT DEFAULT 0 COMMENT '订单数量',
    total_amount DECIMAL(12,2) DEFAULT 0.00 COMMENT '总金额',
    completed_count INT DEFAULT 0 COMMENT '完成数量',
    cancelled_count INT DEFAULT 0 COMMENT '取消数量',
    avg_price DECIMAL(10,2) DEFAULT 0.00 COMMENT '平均单价',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY uk_stat (stat_date, stat_type, service_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='统计汇总表';

-- =============================================
-- 初始化默认服务配置数据
-- =============================================
INSERT INTO t_studio_service_config (service_name, service_code, description, base_price, price_unit, sort_order) VALUES
('歌曲分离', 'song_split', '人声与伴奏分离，提取纯净人声或伴奏轨道', 20.00, '次', 1),
('乐器声分离', 'instrument_split', '可指定分离特定乐器声音（吉他、钢琴、鼓等）', 30.00, '次', 2),
('歌曲润色', 'song_polish', '对客户提供的录音文件进行专业润色加工', 50.00, '次', 3),
('DJ编曲', 'dj_remix', '根据客户指定曲风进行音乐编制', 100.00, '次', 4),
('歌曲代找', 'song_search', '按客户需求查找特定歌曲资源', 10.00, '次', 5)
ON DUPLICATE KEY UPDATE service_name = VALUES(service_name);

-- =============================================
-- 初始化默认问候语
-- =============================================
INSERT INTO t_studio_greeting_config (greeting_text, greeting_type, send_time, is_random) VALUES
('早安！亲爱的歌友们！🌞 新的一天，让我们一起用歌声点亮生活！想唱什么歌尽管说，我来帮您找伴奏！', 'morning', '08:00:00', 0),
('上午好！🎤 这里是歌曲分离工作室，有任何歌曲需求随时找我哦！', 'morning', '10:00:00', 0),
('下午好！🎶 喝茶听歌好时光，需要找歌、分离伴奏、润色录音？找我就对了！', 'evening', '15:00:00', 0),
('晚上好！🌟 忙碌了一天，唱首歌放松一下吧！需要什么歌曲服务随时找我！', 'evening', '19:00:00', 0)
ON DUPLICATE KEY UPDATE greeting_text = VALUES(greeting_text);
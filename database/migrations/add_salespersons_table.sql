-- 销售人员管理表
CREATE TABLE IF NOT EXISTS t_salesperson (
    id INT PRIMARY KEY AUTO_INCREMENT COMMENT '销售人员ID',
    user_id INT NOT NULL COMMENT '所属用户ID',
    name VARCHAR(100) NOT NULL COMMENT '姓名',
    phone VARCHAR(20) COMMENT '联系电话',
    region VARCHAR(100) COMMENT '负责区域',
    route_id INT COMMENT '关联线路ID',
    license_codes JSON COMMENT '关联授权码列表',
    total_sales INT DEFAULT 0 COMMENT '累计销售订单数',
    total_amount DECIMAL(12, 2) DEFAULT 0.00 COMMENT '累计销售金额',
    is_active TINYINT DEFAULT 1 COMMENT '是否启用: 1-启用, 0-禁用',
    remark TEXT COMMENT '备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 外键约束
    FOREIGN KEY (user_id) REFERENCES t_user_account(id) ON DELETE CASCADE,
    FOREIGN KEY (route_id) REFERENCES t_delivery_route(id) ON DELETE SET NULL,
    
    -- 索引
    INDEX idx_user_id (user_id),
    INDEX idx_route_id (route_id),
    INDEX idx_phone (phone),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='销售人员表';

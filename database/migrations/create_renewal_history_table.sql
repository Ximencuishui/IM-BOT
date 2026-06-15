-- 续费历史记录表创建脚本
CREATE TABLE IF NOT EXISTS t_renewal_history (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '记录ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    license_id BIGINT NOT NULL COMMENT '授权码ID',
    order_no VARCHAR(64) COMMENT '订单号',
    trade_no VARCHAR(64) COMMENT '交易号',
    renew_type VARCHAR(20) NOT NULL COMMENT '续费类型: manual-手动, auto-自动, batch-批量',
    period VARCHAR(20) NOT NULL COMMENT '续费周期: 1m, 3m, 6m, 1y',
    months INT NOT NULL COMMENT '续费月数',
    amount DECIMAL(10, 2) NOT NULL COMMENT '支付金额',
    discount DECIMAL(5, 2) DEFAULT 1.0 COMMENT '折扣率',
    old_expiry DATETIME COMMENT '原过期时间',
    new_expiry DATETIME NOT NULL COMMENT '新过期时间',
    payment_method VARCHAR(20) DEFAULT 'alipay' COMMENT '支付方式: alipay, wechat, manual, auto_renew',
    status VARCHAR(20) DEFAULT 'success' COMMENT '状态: success, failed, pending',
    error_message TEXT COMMENT '错误信息',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    paid_at DATETIME COMMENT '支付完成时间',
    
    INDEX idx_user_id (user_id),
    INDEX idx_license_id (license_id),
    INDEX idx_created_at (created_at),
    INDEX idx_status (status),
    FOREIGN KEY (user_id) REFERENCES t_user_account(id),
    FOREIGN KEY (license_id) REFERENCES t_license_v2(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='续费历史记录表';

-- 为续费历史查询添加复合索引
CREATE INDEX idx_user_created ON t_renewal_history (user_id, created_at);
CREATE INDEX idx_license_created ON t_renewal_history (license_id, created_at);

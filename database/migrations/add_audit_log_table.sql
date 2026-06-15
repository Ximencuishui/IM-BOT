-- 创建审计日志表
CREATE TABLE IF NOT EXISTS `t_audit_log` (
  `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '日志ID',
  `user_id` INT COMMENT '操作用户ID',
  `username` VARCHAR(50) COMMENT '操作用户名',
  `action` VARCHAR(50) NOT NULL COMMENT '操作类型: login-登录, logout-登出, create-创建, update-更新, delete-删除, export-导出',
  `resource` VARCHAR(50) COMMENT '操作资源: user-用户, license-授权码, order-订单, product-商品, config-配置',
  `resource_id` INT COMMENT '资源ID',
  `description` VARCHAR(500) COMMENT '操作描述',
  `old_value` TEXT COMMENT '旧值(JSON)',
  `new_value` TEXT COMMENT '新值(JSON)',
  `ip_address` VARCHAR(50) COMMENT 'IP地址',
  `user_agent` VARCHAR(500) COMMENT '用户代理',
  `status` VARCHAR(20) DEFAULT 'success' COMMENT '操作状态: success-成功, failed-失败',
  `error_message` TEXT COMMENT '错误信息',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
  INDEX `idx_user_id` (`user_id`),
  INDEX `idx_action` (`action`),
  INDEX `idx_resource` (`resource`),
  INDEX `idx_created_at` (`created_at`),
  FOREIGN KEY (`user_id`) REFERENCES `t_user_account`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='审计日志表';

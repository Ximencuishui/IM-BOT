-- 授权码表自动续费功能迁移脚本
-- 添加自动续费相关字段到 t_license_v2 表

ALTER TABLE t_license_v2 
ADD COLUMN auto_renew TINYINT(1) DEFAULT 0 COMMENT '是否自动续费',
ADD COLUMN renew_period VARCHAR(20) DEFAULT NULL COMMENT '续费周期: 1m-1个月, 3m-3个月, 6m-6个月, 1y-1年',
ADD COLUMN last_renewed_at DATETIME DEFAULT NULL COMMENT '上次续费时间';

-- 添加索引以优化自动续费查询性能
CREATE INDEX idx_auto_renew ON t_license_v2 (auto_renew, is_active, is_revoked, expires_at);

-- 更新说明
-- 1. auto_renew: 布尔值，表示是否启用自动续费
-- 2. renew_period: 续费周期，可选值：1m, 3m, 6m, 1y
-- 3. last_renewed_at: 记录上次自动续费的时间

-- 为商品表添加属性、佣金、积分字段
-- 执行时间：2026-04-16

USE food_delivery;

-- 添加商品属性字段（JSON格式，最多10个属性）
ALTER TABLE t_product ADD COLUMN attributes JSON COMMENT '商品属性JSON数组,最多10个属性,如: [{"name":"颜色","value":"红色"},{"name":"尺码","value":"L"}]' AFTER category;

-- 添加佣金字段
ALTER TABLE t_product ADD COLUMN commission DECIMAL(10, 2) DEFAULT 0.00 COMMENT '佣金(元)' AFTER attributes;

-- 添加积分字段
ALTER TABLE t_product ADD COLUMN points INT DEFAULT 0 COMMENT '积分' AFTER commission;

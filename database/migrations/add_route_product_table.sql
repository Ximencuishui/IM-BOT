-- 迁移脚本: 添加线路产品关联表和订单调整日志表
-- 创建时间: 2026-04-15

-- 1. 创建线路产品关联表
CREATE TABLE IF NOT EXISTS t_route_product (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID',
    route_id INT NOT NULL COMMENT '配送线路ID',
    product_id BIGINT NOT NULL COMMENT '商品ID',
    sort_order INT DEFAULT 0 COMMENT '排序序号(用于圈选时的1-10编号)',
    custom_price DECIMAL(10, 2) COMMENT '线路专属价格(NULL则使用商品基础价)',
    is_active TINYINT DEFAULT 1 COMMENT '是否启用',
    created_at DATETIME DEFAULT NOW() COMMENT '创建时间',
    updated_at DATETIME DEFAULT NOW() ON UPDATE NOW() COMMENT '更新时间',

    UNIQUE KEY uk_route_product (route_id, product_id),
    INDEX idx_route_sort (route_id, sort_order),
    FOREIGN KEY (route_id) REFERENCES t_delivery_route(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES t_product(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='线路产品关联表';

-- 2. 创建订单数量调整日志表
CREATE TABLE IF NOT EXISTS t_order_adjustment_log (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT 'ID',
    order_id BIGINT NOT NULL COMMENT '关联订单ID',
    customer_id INT NOT NULL COMMENT '客户ID',
    product_id BIGINT NOT NULL COMMENT '商品ID',
    adjustment_type VARCHAR(20) NOT NULL COMMENT '调整类型: add/subtract/replace',
    quantity_change DECIMAL(10, 2) NOT NULL COMMENT '数量变化(+/-)',
    original_quantity DECIMAL(10, 2) COMMENT '调整前数量',
    new_quantity DECIMAL(10, 2) COMMENT '调整后数量',
    operator VARCHAR(50) COMMENT '操作人',
    reason VARCHAR(255) COMMENT '调整原因',
    created_at DATETIME DEFAULT NOW() COMMENT '创建时间',

    INDEX idx_customer_product_date (customer_id, product_id, created_at),
    FOREIGN KEY (order_id) REFERENCES t_order(id) ON DELETE CASCADE,
    FOREIGN KEY (customer_id) REFERENCES t_user(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES t_product(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单数量调整日志';

-- 3. 插入示例数据(可选)
-- 为线路1分配前10个商品作为示例
INSERT INTO t_route_product (route_id, product_id, sort_order, custom_price, is_active)
SELECT
    1 AS route_id,
    p.id AS product_id,
    ROW_NUMBER() OVER (ORDER BY p.id) AS sort_order,
    NULL AS custom_price,
    1 AS is_active
FROM t_product p
WHERE p.is_active = 1
LIMIT 10
ON DUPLICATE KEY UPDATE sort_order = VALUES(sort_order);

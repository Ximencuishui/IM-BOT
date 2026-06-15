-- 添加定价套餐表
CREATE TABLE IF NOT EXISTS t_pricing_package (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    package_name VARCHAR(100) NOT NULL,
    includes_desktop BOOLEAN DEFAULT 0,
    license_count INTEGER DEFAULT 0,
    validity_months INTEGER DEFAULT 1,
    price DECIMAL(10,2) NOT NULL,
    description VARCHAR(500),
    is_active BOOLEAN DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 插入默认套餐数据
INSERT INTO t_pricing_package (package_name, includes_desktop, license_count, validity_months, price, description, is_active, sort_order) VALUES
('基础版', 0, 1, 1, 100.00, '包含1个授权码，有效期1个月', 1, 1),
('标准版', 0, 3, 3, 270.00, '包含3个授权码，有效期3个月，享受9折优惠', 1, 2),
('专业版', 0, 6, 6, 480.00, '包含6个授权码，有效期6个月，享受8折优惠', 1, 3),
('企业版', 1, 12, 12, 800.00, '包含桌面端年费 + 12个授权码，有效期12个月', 1, 4);

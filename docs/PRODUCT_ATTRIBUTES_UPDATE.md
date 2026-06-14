# 商品属性与统计参数功能更新说明

## 更新日期
2026-04-16

## 功能说明
本次更新为商品管理模块添加了以下新功能：

### 1. 商品属性功能
- 允许为每个商品添加最多10个自定义属性（如颜色、尺码等）
- 属性以键值对形式存储：`{"name": "颜色", "value": "红色"}`
- 支持动态添加和删除属性

### 2. 统计参数
- **佣金**：可为每个商品设置佣金金额（元），用于财务统计
- **积分**：可为每个商品设置积分值，用于积分系统统计

## 数据库变更

### 新增字段
在 `t_product` 表中新增以下字段：
- `attributes` (JSON) - 商品属性数组，最多10个属性
- `commission` (DECIMAL 10,2) - 佣金金额，默认0.00
- `points` (INT) - 积分值，默认0

### 应用数据库迁移
执行以下SQL脚本更新数据库：
```sql
-- 路径：database/migrations/add_product_attributes.sql
source database/migrations/add_product_attributes.sql;
```

或手动执行：
```sql
USE food_delivery;

-- 添加商品属性字段（JSON格式，最多10个属性）
ALTER TABLE t_product ADD COLUMN attributes JSON COMMENT '商品属性JSON数组,最多10个属性,如: [{"name":"颜色","value":"红色"},{"name":"尺码","value":"L"}]' AFTER category;

-- 添加佣金字段
ALTER TABLE t_product ADD COLUMN commission DECIMAL(10, 2) DEFAULT 0.00 COMMENT '佣金(元)' AFTER attributes;

-- 添加积分字段
ALTER TABLE t_product ADD COLUMN points INT DEFAULT 0 COMMENT '积分' AFTER commission;
```

## 前端界面更新

### 添加商品对话框
- 新增"佣金(元)"输入框
- 新增"积分"输入框  
- 新增"商品属性"区域，支持动态添加/删除属性（最多10个）

### 编辑商品对话框
- 同样添加了佣金、积分和商品属性功能
- 编辑时会加载商品现有的属性和统计参数

## 后端API更新

### 创建商品 API
`POST /api/admin/products`
- 新增支持字段：`attributes`, `commission`, `points`

### 更新商品 API
`PUT /api/admin/products/<id>`
- 新增支持字段：`attributes`, `commission`, `points`

### 获取商品列表 API
`GET /api/admin/products`
- 返回数据中现在包含 `attributes`, `commission`, `points` 字段

## 使用示例

### 添加带属性的商品
```json
{
  "product_name": "T恤",
  "unit": "件",
  "price": 59.90,
  "category": "服装",
  "shortcut_codes": ["TX", "T恤"],
  "commission": 5.00,
  "points": 100,
  "sort_order": 1,
  "attributes": [
    {"name": "颜色", "value": "红色"},
    {"name": "尺码", "value": "L"},
    {"name": "材质", "value": "纯棉"}
  ]
}
```

### 数据验证
- 商品属性数量不得超过10个
- 佣金和积分必须为非负数
- 属性名称和值不能为空

## 注意事项
1. 确保MySQL版本为5.7+以支持JSON字段类型
2. 更新后旧的统计数据不受影响，新字段默认值为0或空数组
3. 属性数据以JSON格式存储，便于扩展和查询

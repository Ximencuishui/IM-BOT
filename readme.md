# 本地化配送服务商智能订货统计工具  
## 基于大模型AI技术的自动化订单处理平台

**版本**:V2.0.0  
**日期**:2026年4月  
**状态**:核心功能已完成，进入测试优化阶段

**架构说明**: 本项目采用 **网站端 + 桌面端** 分离架构
- **网站端** (`frontend/`): 产品介绍、用户注册登录、授权购买、文件下载、用户中心（含授权码管理、自动续费、统计分析）
- **桌面端** (本地Python服务): 订单管理、商品管理、客户管理、机器人配置、数据看板、报表导出

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术架构](#2-技术架构)
3. [网站端与桌面端职责划分](#3-网站端与桌面端职责划分)
4. [核心功能模块](#4-核心功能模块)
5. [系统架构设计](#5-系统架构设计)
6. [数据库设计](#6-数据库设计)
7. [API 接口文档](#7-api-接口文档)
8. [部署指南](#8-部署指南)
9. [授权系统](#9-授权系统)
10. [新增功能：授权码管理增强](#10-新增功能授权码管理增强)
11. [VXHook 集成](#11-vxhook-集成)
12. [风险与应对](#12-风险与应对)
13. [开发进展](#13-开发进展)

---

## 1. 项目概述

### 1.1 项目背景
小吃店食材配送业务中,客户通过微信群发送订单(口语化描述、快捷码等),传统方式需人工统计后录入系统,效率低且易出错。本系统通过大模型AI技术自动捕获群聊消息,利用自然语言处理技术解析订单,实现从消息接收到报表生成的全流程自动化。

### 1.2 核心目标
- **消息自动捕获**: 通过本地消息接入实时捕获微信群订单消息
- **智能订单解析**: 支持自然语言、快捷码、批量语法等多种解析模式
- **多租户授权管理**: 本地部署 + 云端授权模式,每个微信群独立授权
- **自动化报表**: 定时生成 Excel 报表并推送到指定渠道
- **数据看板**: 实时监控订单趋势、销售排行、客户分布

### 1.3 技术特点
- **纯 Python 实现**: 后端采用 Flask + SQLAlchemy,无需 Java 环境
- **灵活数据库**: 默认 SQLite(零配置),可选 MySQL
- **降级容错**: Redis/RabbitMQ/ES 未安装时自动降级,核心功能不受影响
- **规则引擎**: 支持解析规则、统计规则、回复规则的动态配置
- **jieba 分词**: 集成中文分词库,提升商品匹配准确率

---

## 2. 技术架构

### 2.1 网站端与桌面端职责划分

本项目严格遵循**标准开源项目架构**,网站端与桌面端功能完全隔离:

#### 网站端 (`frontend/` 目录)
**定位**: 产品展示、用户管理、授权销售平台  
**部署位置**: 公网服务器(如阿里云/腾讯云)  
**技术栈**: HTML + Vue 3 + Element Plus (CDN引入)  

**核心功能**:
- 📄 **产品介绍**: 功能展示、技术架构说明、下载引导
- 👤 **用户注册/登录**: 账号管理、JWT认证
- 💳 **授权购买**: 选择套餐(月付/年付)、在线支付、生成授权码
- 📥 **应用下载**: Windows/Linux/Docker版本下载链接
- 👤 **用户中心**：
  - 个人信息管理(邮箱、手机号、密码修改)
  - 授权码管理(查看、续期、撤销、批量展期)
  - 销售员信息显示(桌面端同步)
  - 自动续费设置(1个月/3个月/6个月/1年)
  - 续费历史记录查询
  - 统计分析(概览、趋势、续费分析)
  - 订阅管理(查看订阅状态、历史订单)
  - 备份文件管理(规则配置上传/下载)

**不包含的功能**:
- ❌ 订单管理
- ❌ 商品管理
- ❌ 客户管理
- ❌ 机器人配置
- ❌ 数据看板
- ❌ 报表导出

#### 桌面端 (本地Python服务)
**定位**: 业务处理核心,用户本地部署  
**部署位置**: 用户本地电脑/内网服务器  
**技术栈**: Python Flask + SQLAlchemy + SQLite  

**核心功能**:
- 📨 **消息接收**: HTTP/TCP接收微信Hook推送的消息
- 🧠 **订单解析**: jieba分词、自然语言处理、快捷码匹配
- 📦 **订单管理**: CRUD、批量圈选、增量订单
- 🥬 **商品管理**: 商品库、快捷码配置、价格管理
- 👥 **客户管理**: 客户档案、微信群绑定、线路关联
- 🤖 **机器人配置**: Hook开关、回复规则、智能指令
- 📊 **数据看板**: 订单趋势、商品排行、客户分布
- 📈 **报表导出**: Excel多Sheet、按线路/销售汇总
- ⏰ **定时任务**: 每日截单、邮件推送、消息清理

**不依赖的功能**:
- ❌ 用户注册登录(桌面端使用演示账号或本地配置)
- ❌ 在线支付(授权码从网站端购买后在桌面端激活)
- ❌ 云端数据存储(所有数据存储在本地SQLite/MySQL)

#### 数据流向

```
用户访问流程:
  网站端 (注册账号 → 购买授权 → 下载桌面端)
              ↓
  桌面端 (安装运行 → 激活授权码 → 开始使用)

授权验证流程:
  桌面端 (提交授权码 + 机器指纹)
      ↓
  网站端API (验证授权有效性)
      ↓
  返回结果 (允许/拒绝使用)

业务数据流:
  桌面端本地处理 (订单/商品/客户数据)
      ↓
  本地SQLite/MySQL存储
      ↓
  不上传到网站端 (数据完全私有)
```

### 2.2 总体技术栈

#### 网站端技术栈
| 层次 | 技术选型 | 说明 |
|------|----------|------|
| 前端框架 | Vue 3 (CDN) | 响应式数据绑定 |
| UI组件 | Element Plus | 企业级组件库 |
| HTTP客户端 | Axios | API调用 |
| 后端API | Python Flask / Node.js | 用户管理、授权销售(待开发) |
| 数据库 | MySQL / PostgreSQL | 用户信息、授权记录(网站端) |
| 支付网关 | 支付宝/微信支付 | 在线购买授权(待对接) |

#### 桌面端技术栈
| 层次 | 技术选型 | 状态 |
|------|----------|------|
| 消息捕获 | 本地消息接入 (C++ DLL,需外部提供) | ⏳ 待集成 |
| 消息接收适配 | Python Flask (`core/appV2.py`) / TCP Server (`core/tcp_serverV2.py`) | ✅ 已完成 |
| 后端业务 | Python 3.8+ + Flask 2.x + SQLAlchemy | ✅ 已完成 |
| 数据库 | SQLite 3 (默认) / MySQL 8.0+ (可选) | ✅ 已完成 |
| 缓存 (可选) | Redis 7.0+ (消息去重) | ✅ 已支持(可选) |
| 消息队列 (可选) | RabbitMQ 3.x (削峰填谷) | ✅ 已支持(可选) |
| 日志检索 (可选) | Elasticsearch 8.x (原始消息存储) | ✅ 已支持(可选) |
| 前端界面 | HTML + Vue 3 (本地访问) | ✅ 原型可用 |
| 部署方式 | 单机部署 / Docker Compose | ✅ 已完成 |

### 2.3 与原文档的差异说明

| 对比项 | 原文档设计 | 实际实现 |
|--------|-----------|---------|
| 后端语言 | Java 17 + Spring Boot 3 | **Python Flask** |
| 数据库 | 仅 MySQL | **SQLite(默认) + MySQL(可选)** |
| 中间件依赖 | 必须 Redis/RabbitMQ/ES | **可选,支持降级运行** |
| 前端框架 | Vue 3 + Element Plus | **HTML 原型(待完善)** |
| 部署拓扑 | Windows + Linux 云分离 | **单机/Docker 一体化** |
| 授权系统 | 未提及 | **已实现多租户授权** |
| 规则引擎 | 未提及 | **已实现动态规则配置** |
| 机器人功能 | 未提及 | **已实现Hook配置管理** |

---

## 3. 核心功能模块

### 3.1 已完成的 API 模块 (14个蓝图)

| 模块名称 | 路由前缀 | 代码量 | 完成度 | 功能说明 |
|---------|---------|-------|-------|---------|
| 订单管理 | `/api/orders` | 13.6 KB | 95% | CRUD、解析创建、增量订单、批量圈选、日报汇总 |
| 商品管理 | `/api/products` | 4.2 KB | 90% | 商品CRUD、搜索、快捷码管理 |
| 客户管理 | `/api/customers` | 4.3 KB | 90% | 客户CRUD、微信群绑定、线路关联 |
| 报表管理 | `/api/reports` | 6.7 KB | 85% | 日报导出、线路汇总、销售汇总、Excel多Sheet |
| 用户认证 | `/api/auth` | 5.6 KB | 95% | 注册、登录、JWT验证、演示账号初始化 |
| 授权管理V2 | `/api/license/v2` | 6.0 KB | 90% | 多租户授权、团队分配、机器绑定 |
| 团队管理 | `/api/team` | 4.4 KB | 90% | 销售员CRUD、授权分配、团队成员管理 |
| 机器人配置 | `/api/robot` | 15.3 KB | 95% | Hook配置、启停控制、回复规则、智能指令 |
| 规则配置 | `/api/rules` | 6.5 KB | 90% | 解析规则/统计规则CRUD、优先级管理 |
| 数据看板 | `/api/dashboard` | 6.1 KB | 90% | 概览统计、趋势图表、商品排行、客户分布 |
| 规则模板 | `/api/rule-templates` | 5.6 KB | 85% | 模板库浏览、下载计数、上传分享 |
| 规则导入 | `/api/rule-import` | 20.3 KB | 90% | CSV/TXT/MD多格式导入、预览、冲突处理 |
| 线路产品 | `/api/routes` | 4.6 KB | 90% | 配送线路CRUD、产品关联管理 |
| 授权管理(旧) | `/api/license` | 3.0 KB | 80% | 兼容旧版授权接口 |

**总计**: 约 60+ REST API 端点

### 3.2 已实现的业务服务 (20个服务类)

| 服务名称 | 代码量 | 完成度 | 核心功能 |
|---------|-------|-------|---------|
| order_service.py | 19.3 KB | 95% | 订单CRUD、幂等性、增量订单、批量圈选、客户日报 |
| order_parser.py | 16.0 KB | 90% | 商品匹配(精确/快捷码/jieba)、数量提取、备注解析、批量语法 |
| robot_service.py | 15.5 KB | 90% | Hook配置管理、启停控制、回复规则匹配、智能指令处理 |
| rule_file_parser.py | 19.7 KB | 90% | CSV/TXT/MD多格式解析、语法验证、规则转换 |
| rule_import.py | 20.3 KB | 90% | 导入流程编排、冲突检测、批量导入、备份恢复 |
| dashboard_service.py | 9.7 KB | 90% | 概览统计、销售趋势、商品排行、客户分布分析 |
| command_config_service.py | 13.3 KB | 90% | 指令CRUD、关键词/正则匹配、使用统计 |
| license_service.py | 12.0 KB | 90% | 授权码生成、激活、过期检查、机器指纹绑定 |
| robot_report_service.py | 12.5 KB | 85% | 销售员报表、客户订单详情、文本报表生成 |
| scheduler.py | 10.7 KB | 90% | 每日截单任务、报表生成、邮件发送、消息清理 |
| message_service.py | 8.1 KB | 90% | Redis去重、RabbitMQ推送、ES写入、降级处理 |
| customer_service.py | 7.2 KB | 90% | 客户CRUD、微信群绑定查询、线路关联 |
| product_service.py | 6.9 KB | 90% | 商品CRUD、快捷码搜索、价格管理 |
| route_product_service.py | 7.8 KB | 90% | 线路产品关联、配送范围管理 |
| auth_service.py | 5.6 KB | 95% | bcrypt密码哈希、JWT令牌、登录装饰器 |
| rule_service.py | 5.9 KB | 90% | 解析规则/统计规则CRUD、规则启用禁用 |
| rule_template_service.py | 5.4 KB | 85% | 模板CRUD、下载计数、分类管理 |
| license_service_v2.py | 9.5 KB | 85% | 多租户授权管理、团队级授权分配 |
| team_service.py | 5.0 KB | 90% | 团队成员CRUD、角色权限管理 |
| cloud_sync_service.py | 6.5 KB | 70% | 规则备份/恢复(框架已搭建,需对接云服务) |

### 3.3 数据模型 (21张数据库表)

**核心业务表** (8张):
- `delivery_route`: 配送线路
- `product`: 商品信息(含快捷码)
- `customer`: 客户档案(含微信群绑定)
- `order`: 订单主表
- `order_item`: 订单明细
- `order_adjustment_log`: 订单调整日志
- `route_product`: 线路产品关联
- `raw_message`: 原始消息记录

**用户与授权表** (4张):
- `user`: 用户账户(bcrypt密码哈希)
- `license`: 授权码(机器绑定、有效期管理)
- `team_member`: 团队成员(销售员信息)
- `system_config`: 系统配置

**机器人配置表** (3张):
- `robot_config`: 机器人Hook配置
- `reply_rule`: 自动回复规则
- `report_push_log`: 报表推送日志

**规则系统表** (4张):
- `parse_rule`: 订单解析规则
- `stat_rule`: 统计分析规则
- `rule_template`: 规则模板库
- `user_rule_backup`: 用户规则备份

**指令配置表** (1张):
- `command_config`: 智能指令配置(关键词/正则匹配)

### 3.4 缺失部分

- **消息捕获引擎 DLL**: C++实现的消息捕获模块,需外部提供或使用开源方案
- **完整前端工程**: 当前仅有 HTML 原型(`frontend/` 目录),缺少 Vue/React 完整前端
- **云端同步服务**: `cloud_sync_service.py` 框架已搭建,需对接实际云存储(API暂未实现)
- **测试覆盖**: 有基础单元测试,但覆盖率偏低(约30%),缺少API集成测试

---

## 4. 系统架构设计

### 4.1 架构图

```
[微信群] --> [PC微信客户端] 
                ↓ (Hook注入)
         [Hook DLL] 捕获文本消息
                ↓ (HTTP POST / TCP 长连接)
    [消息接收服务] appV2.py / tcp_serverV2.py
                ↓ (Redis去重 → RabbitMQ推送 → ES存储)
         [订单解析服务] (消费MQ,调用NLP解析)
                ↓ (授权检查 → 规则引擎处理)
         [订单服务] 写 SQLite/MySQL + Redis缓存
                ↓
    [定时调度器] 每日截单 → 生成Excel → 邮件推送
                ↓
         [REST API] 供前端/第三方调用
```

### 4.2 数据流说明

1. **消息捕获**: 客户在微信群发送消息,PC微信收到后,Hook DLL 读取消息内容(发送者昵称、群ID、文本内容、时间戳)

2. **消息接收**: Hook DLL 将消息封装为 JSON,通过 HTTP POST 发送到 `http://127.0.0.1:5000/api/recvMsg` (appV2.py) 或 TCP 长连接(tcp_serverV2.py)

3. **消息预处理**: 
   - Redis 去重(基于消息ID或时间戳+内容MD5,TTL可配置)
   - 写入 Elasticsearch(原始消息审计,可选)
   - 推送到 RabbitMQ 队列 `order.raw`(持久化,可选)
   - 降级方案:无Redis时跳过,无RabbitMQ时直接同步处理

4. **订单解析**: 
   - 从队列拉取消息,根据 `group_id` 查询对应客户(若无则记录异常)
   - 调用订单解析器: jieba分词 → 商品匹配(精确/快捷码/模糊) → 数量提取 → 备注识别
   - 置信度阈值过滤,低置信度进入人工审核队列

5. **授权检查**: 创建订单前检查该微信群是否有有效授权码,未授权返回 403

6. **订单入库**: 调用订单服务 API,根据 `order_uuid` 幂等创建/更新当日订单,写入 SQLite/MySQL

7. **报表生成**: 每日 21:30 定时任务触发,按线路/销售分组生成 Excel 多Sheet报表,邮件推送到指定邮箱

8. **前端展示**: 销售通过管理后台查看订单、修改数量、导出数据看板

---

## 5. 数据库设计

### 5.1 核心业务表

#### 商品表 (product)
```sql
CREATE TABLE product (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name VARCHAR(100) NOT NULL,          -- 商品名称
    shortcut_codes TEXT,                         -- 快捷码(JSON数组:["TD","土","土豆"])
    unit VARCHAR(20) DEFAULT '斤',              -- 默认单位
    price DECIMAL(10,2),                        -- 单价
    category VARCHAR(50),                       -- 分类(蔬菜/肉类/调料等)
    is_active BOOLEAN DEFAULT 1,                -- 是否启用
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_product_name ON product(product_name);
```

#### 客户表 (customer)
```sql
CREATE TABLE customer (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name VARCHAR(100) NOT NULL,        -- 客户名称
    phone VARCHAR(20),                          -- 联系电话
    address TEXT,                               -- 配送地址
    sales_person VARCHAR(50),                   -- 所属销售
    delivery_route_id INTEGER,                  -- 配送线路ID
    wx_group_id VARCHAR(64),                    -- 微信群ID
    wx_alias VARCHAR(64),                       -- 微信昵称
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (delivery_route_id) REFERENCES delivery_route(id)
);
CREATE INDEX idx_wx_group_id ON customer(wx_group_id);
```

#### 订单表 (order)
```sql
CREATE TABLE "order" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_uuid VARCHAR(64) UNIQUE,              -- 幂等性标识
    customer_id INTEGER NOT NULL,
    order_date DATE NOT NULL,                   -- 订单日期
    total_amount DECIMAL(10,2) DEFAULT 0,       -- 订单总额
    status VARCHAR(20) DEFAULT 'pending',       -- pending/confirmed/cancelled
    source VARCHAR(20) DEFAULT 'wechat',        -- 来源(wechat/manual/api)
    remark TEXT,                                -- 备注
    created_by INTEGER,                         -- 创建人ID
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customer(id),
    FOREIGN KEY (created_by) REFERENCES user(id)
);
CREATE INDEX idx_order_date ON "order"(order_date);
CREATE INDEX idx_customer_order ON "order"(customer_id, order_date);
```

#### 订单明细表 (order_item)
```sql
CREATE TABLE order_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity DECIMAL(10,2) NOT NULL,            -- 数量
    unit VARCHAR(20),                           -- 单位(覆盖商品默认单位)
    unit_price DECIMAL(10,2),                   -- 下单时单价
    subtotal DECIMAL(10,2),                     -- 小计
    remark TEXT,                                -- 商品备注(要嫩的/不要葱)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES "order"(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES product(id)
);
```

### 5.2 用户与授权表

#### 用户表 (user)
```sql
CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,        -- bcrypt哈希
    email VARCHAR(100),
    role VARCHAR(20) DEFAULT 'sales',           -- admin/sales/viewer
    is_active BOOLEAN DEFAULT 1,
    last_login_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### 授权码表 (license)
```sql
CREATE TABLE license (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    license_code VARCHAR(64) UNIQUE NOT NULL,   -- 授权码(ABC123-DEF456-GHI789)
    machine_id VARCHAR(64),                     -- 机器指纹
    bound_to VARCHAR(64),                       -- 绑定对象(微信群ID)
    license_type VARCHAR(20),                   -- monthly/yearly
    activated_at DATETIME,                      -- 激活时间
    expires_at DATETIME,                        -- 到期时间
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_bound_to ON license(bound_to);
CREATE INDEX idx_expires_at ON license(expires_at);
```

### 5.3 机器人配置表

#### 机器人配置表 (robot_config)
```sql
CREATE TABLE robot_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    robot_name VARCHAR(100) NOT NULL,
    group_id VARCHAR(64) UNIQUE NOT NULL,       -- 绑定的微信群ID
    hook_enabled BOOLEAN DEFAULT 0,             -- Hook开关
    auto_reply_enabled BOOLEAN DEFAULT 0,       -- 自动回复开关
    parse_enabled BOOLEAN DEFAULT 0,            -- 订单解析开关
    webhook_url TEXT,                           -- 消息转发URL
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 5.4 规则系统表

#### 解析规则表 (parse_rule)
```sql
CREATE TABLE parse_rule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_name VARCHAR(100) NOT NULL,
    rule_type VARCHAR(20),                      -- regex/keyword/jieba
    match_pattern TEXT,                         -- 匹配模式(正则表达式/关键词)
    priority INTEGER DEFAULT 5,                 -- 优先级(1-10,越高越优先)
    is_enabled BOOLEAN DEFAULT 1,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_priority ON parse_rule(priority DESC);
```

---

## 6. API 接口文档

### 6.1 认证接口 (`/api/auth`)

#### 用户注册
```http
POST /api/auth/register
Content-Type: application/json

{
  "username": "admin",
  "password": "your_password",
  "email": "admin@example.com",
  "role": "admin"
}
```

#### 用户登录
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "your_password"
}

Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin"
  }
}
```

### 6.2 订单管理 (`/api/orders`)

#### 创建订单(直接)
```http
POST /api/orders
Authorization: Bearer <token>
Content-Type: application/json

{
  "customer_id": 1,
  "items": [
    {"product_id": 1, "quantity": 10, "unit": "斤", "remark": "要嫩的"},
    {"product_id": 2, "quantity": 5, "unit": "斤"}
  ],
  "order_date": "2026-04-15",
  "remark": "客户急用"
}
```

#### 解析消息创建订单
```http
POST /api/orders/parse
Content-Type: application/json

{
  "group_id": "test_group_001",
  "sender": "张三",
  "content": "来10斤土豆,要嫩的"
}

Response:
{
  "order_id": 123,
  "parsed_items": [
    {"product_id": 1, "product_name": "土豆", "quantity": 10, "confidence": 0.95}
  ]
}
```

#### 查询今日订单
```http
GET /api/orders/today?date=2026-04-15
Authorization: Bearer <token>
```

#### 批量圈选订单
```http
POST /api/orders/batch-select
Authorization: Bearer <token>
Content-Type: application/json

{
  "customer_ids": [1, 2, 3],
  "order_date": "2026-04-15",
  "action": "confirm"  // confirm/cancel
}
```

### 6.3 授权管理 (`/api/license/v2`)

#### 获取机器指纹
```http
GET /api/license/v2/machine-id

Response:
{
  "machine_id": "fae60cfc5913b25a76800648915144ef"
}
```

#### 激活授权
```http
POST /api/license/v2/activate
Content-Type: application/json

{
  "license_code": "ABC123-DEF456-GHI789",
  "bound_to": "group_chat_id_001"
}

Response:
{
  "status": "success",
  "expires_at": "2027-04-15T00:00:00"
}
```

#### 查询授权状态
```http
GET /api/license/v2/status?bound_to=group_chat_id_001

Response:
{
  "is_authorized": true,
  "license_type": "yearly",
  "expires_at": "2027-04-15T00:00:00",
  "days_remaining": 365
}
```

### 6.4 机器人配置 (`/api/robot`)

#### 配置机器人
```http
POST /api/robot/config
Authorization: Bearer <token>
Content-Type: application/json

{
  "robot_name": "订单助手",
  "group_id": "group_chat_id_001",
  "hook_enabled": true,
  "auto_reply_enabled": true,
  "parse_enabled": true
}
```

#### 添加回复规则
```http
POST /api/robot/reply-rules
Authorization: Bearer <token>
Content-Type: application/json

{
  "robot_id": 1,
  "rule_name": "订单确认回复",
  "trigger_type": "keyword",
  "trigger_content": "下单成功",
  "reply_type": "text",
  "reply_content": "已收到您的订单,我们将尽快安排配送",
  "priority": 10
}
```

### 6.5 规则管理 (`/api/rules`)

#### 创建解析规则
```http
POST /api/rules/parse
Authorization: Bearer <token>
Content-Type: application/json

{
  "rule_name": "标准数量+单位+商品",
  "rule_type": "regex",
  "match_pattern": "(\\d+(?:\\.\\d+)?)\\s*(斤|两|kg|公斤|包|箱|瓶)(.+?)(?:,|$)",
  "priority": 10,
  "is_enabled": true
}
```

#### 导入规则文件
```http
POST /api/rule-import/import
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: rules.csv 或 rules.txt 或 rules.md
conflict_strategy: skip/overwrite/rename
```

### 6.6 数据看板 (`/api/dashboard`)

#### 概览统计
```http
GET /api/dashboard/overview?start_date=2026-04-01&end_date=2026-04-15

Response:
{
  "total_orders": 1250,
  "total_revenue": 45600.50,
  "active_customers": 85,
  "avg_order_value": 36.48
}
```

#### 销售趋势
```http
GET /api/dashboard/sales-trend?period=daily&days=30
```

#### 商品排行
```http
GET /api/dashboard/product-ranking?order_date=2026-04-15&limit=10
```

---

## 7. 部署指南

### 7.1 快速启动(推荐新手)

#### Windows
```bash
# 1. 安装Python 3.8+
# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动完整服务(包含所有API)
python main.py

# 或选择启动特定服务
start.bat
# 选项1: HTTP消息接收服务
# 选项2: TCP消息接收服务
# 选项3: 完整业务服务
```

#### Linux/Mac
```bash
chmod +x start.sh
./start.sh
```

### 7.2 Docker Compose 部署(生产环境)

```yaml
# docker-compose.yml 示例
version: '3.8'
services:
  app:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - DB_TYPE=sqlite
      - REDIS_URL=redis://redis:6379
      - RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672
    depends_on:
      - redis
      - rabbitmq

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"
```

```bash
# 一键启动
docker-compose up -d

# 查看日志
docker-compose logs -f app
```

### 7.3 环境变量配置

复制 `.env.example` 为 `.env`, 修改配置:

```env
# 应用模式
APP_MODE=all
DEBUG=false
SECRET_KEY=your-secret-key-change-in-production
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

# 数据库配置
DB_TYPE=sqlite              # sqlite 或 mysql
SQLITE_DB_PATH=data/food_delivery.db
DB_HOST=localhost            # MySQL时使用
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=food_delivery

# Redis配置 (可选)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# RabbitMQ配置 (可选)
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_VHOST=/

# Elasticsearch配置 (可选)
ES_HOST=localhost
ES_PORT=9200
ES_USER=
ES_PASSWORD=

# 日志配置
LOG_LEVEL=INFO
LOG_DIR=logs

# CORS配置
CORS_ORIGINS=*

# 授权服务配置
LICENSE_API_BASE=https://api.fooddelivery.com

# AI 解析配置 (可选)
AI_PARSER_ENABLED=false
AI_PARSER_PROVIDER=custom_http
AI_PARSER_API_URL=
AI_PARSER_API_KEY=
AI_PARSER_MODEL=
AI_PARSER_TIMEOUT=10

# 健康检查配置 (可选)
MIDDLEWARE_HEALTH_TIMEOUT=1.0
```

### 7.3.1 AI 解析配置说明

- `AI_PARSER_ENABLED=true`：启用 AI 解析模块。
- `AI_PARSER_PROVIDER=custom_http`：使用自定义 HTTP AI 提供商。
- `AI_PARSER_API_URL`：AI 提供商接口地址，必须配置。
- `AI_PARSER_API_KEY`：如果服务需要 Token，填入 API Key。
- `AI_PARSER_MODEL`：可选模型名称，由上游 AI 服务支持。
- `AI_PARSER_TIMEOUT`：HTTP 请求超时时间（秒）。
- `MIDDLEWARE_HEALTH_TIMEOUT`：健康检查超时时间（秒），建议在没有 Redis/RabbitMQ/Elasticsearch 时设置为 `1.0`。

当 AI 解析未启用或返回失败时，系统会自动回退到现有的规则 / 分词解析流程。

### 7.3.2 AI 解析运行时配置

可以通过管理员接口动态读取和修改 AI 解析配置，路由为：
- `GET /api/admin/system/ai-parser-config`
- `POST /api/admin/system/ai-parser-config`

请求体示例：
```json
{
  "enabled": true,
  "provider": "custom_http",
  "api_url": "https://your-ai-service/api/parse",
  "api_key": "your-api-key",
  "model": "gpt-4-1",
  "timeout": 10
}
```

### 7.4 首次启动初始化

系统首次启动时会自动:
1. 创建数据库文件 `data/food_delivery.db` (SQLite模式)
2. 初始化数据库表结构(21张表)
3. 创建演示账号:
   - 管理员: `admin` / `admin123`
   - 销售员: `sales01` / `sales123`
4. 插入示例商品数据(土豆、猪肉、白菜等)

---

## 8. 授权系统

### 8.1 商业模式

本系统采用 **本地部署 + 云端授权** 模式:
- 软件在用户本地服务器/电脑运行,数据完全私有
- 需要通过授权码激活使用
- 每个微信群(销售员)需要独立授权

| 授权类型 | 周期 | 适用场景 |
|---------|------|---------|
| 月付授权 | 30天 | 短期试用、季节性业务 |
| 年付授权 | 365天 | 长期运营(享受折扣) |

### 8.2 授权流程

#### Step 1: 获取机器指纹
```bash
curl http://localhost:5000/api/license/v2/machine-id
```

返回:
```json
{
  "machine_id": "fae60cfc5913b25a76800648915144ef"
}
```

#### Step 2: 购买授权码
1. 访问服务网站(示例: https://api.fooddelivery.com)
2. 注册账号并登录
3. 选择授权套餐(月付/年付)
4. 输入机器指纹绑定设备
5. 选择绑定的微信群ID
6. 支付并获得授权码(格式: `ABC123-DEF456-GHI789`)

#### Step 3: 激活授权
```bash
curl -X POST http://localhost:5000/api/license/v2/activate \
  -H "Content-Type: application/json" \
  -d '{
    "license_code": "ABC123-DEF456-GHI789",
    "bound_to": "group_chat_id_001"
  }'
```

### 8.3 授权检查机制

系统在以下操作时会检查授权:
- 接收微信群消息并解析订单
- 创建新订单
- 导出Excel报表

未授权时返回 `403 Forbidden`:
```json
{
  "error": "未找到有效授权",
  "code": "LICENSE_REQUIRED",
  "hint": "请访问 /api/license/v2/activate 激活授权码"
}
```

### 8.4 离线模式

- 已激活的授权可离线使用 **30天**
- 超过30天需联网验证授权状态
- 新授权激活必须网络连接

### 8.5 迁移授权

更换服务器时:
1. 在服务网站解绑原机器(提供原机器ID)
2. 在新服务器获取新机器指纹
3. 重新绑定并激活授权码
4. 原机器授权立即失效

---

## 10. 新增功能：授权码管理增强

### 10.1 功能概述

V2.0版本新增了完整的授权码生命周期管理功能，包括自动续费、续费提醒、历史记录和统计分析。

#### 核心功能清单

✅ **销售员信息显示**
- 在用户控制台显示授权码绑定的销售员信息
- 支持从桌面端同步销售员数据
- 显示销售员姓名、电话、微信号

✅ **自动续费功能**
- 支持单个授权码启用/禁用自动续费
- 批量展期时可同时设置自动续费
- 多种续费周期选择（1个月/3个月/6个月/1年）
- 折扣机制（长期续费享受优惠）
- 定时任务自动执行续费（每天凌晨2点）

✅ **续费提醒通知**
- 多级提醒策略（提前30天/14天/7天/3天）
- 邮件+短信双渠道通知
- 自动续费成功后发送确认通知
- 定时任务每天上午9点执行

✅ **续费历史记录**
- 完整记录每次续费详情
- 支持分页查询和多维度筛选
- 按授权码、时间范围、续费类型查询
- 统计总续费次数、金额、平均值

✅ **统计分析功能**
- 概览统计：总授权码数、活跃/过期数量
- 销售员统计：每个销售员的授权码分布
- 趋势分析：按日/周/月统计增长趋势
- 续费分析：续费率、平均金额、自动续费率

✅ **支付宝支付集成（预留）**
- 预留支付API接口结构
- 提供完整的集成指南文档
- 上线时只需配置密钥即可启用

### 10.2 技术实现

#### 数据库变更

**License表新增字段：**
```sql
ALTER TABLE t_license_v2 
ADD COLUMN auto_renew TINYINT(1) DEFAULT 0 COMMENT '是否自动续费',
ADD COLUMN renew_period VARCHAR(20) COMMENT '续费周期: 1m, 3m, 6m, 1y',
ADD COLUMN last_renewed_at DATETIME COMMENT '上次续费时间';
```

**新增续费历史表：**
```sql
CREATE TABLE t_renewal_history (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    license_id BIGINT NOT NULL,
    renew_type VARCHAR(20) NOT NULL,  -- manual/auto/batch
    period VARCHAR(20) NOT NULL,      -- 1m/3m/6m/1y
    months INT NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    discount DECIMAL(5, 2) DEFAULT 1.0,
    old_expiry DATETIME,
    new_expiry DATETIME NOT NULL,
    payment_method VARCHAR(20),
    status VARCHAR(20) DEFAULT 'success',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    paid_at DATETIME
);
```

#### 新增API接口

**授权码同步（2个）**
- `POST /api/license/sync/from-desktop` - 从桌面端同步授权码
- `GET /api/license/sync/status` - 查询同步状态

**自动续费管理（5个）**
- `POST /api/auto-renew/enable` - 启用自动续费
- `POST /api/auto-renew/disable` - 禁用自动续费
- `POST /api/auto-renew/batch-enable` - 批量启用
- `GET /api/auto-renew/status` - 查询状态
- `POST /api/auto-renew/calculate-price` - 计算价格

**续费历史（3个）**
- `GET /api/renewal-history/list` - 历史记录列表
- `GET /api/renewal-history/stats` - 统计数据
- `GET /api/renewal-history/license/<id>` - 特定授权码历史

**统计分析（4个）**
- `GET /api/license-stats/overview` - 概览统计
- `GET /api/license-stats/salesperson` - 销售员统计
- `GET /api/license-stats/trend` - 趋势分析
- `GET /api/license-stats/renewal-analysis` - 续费分析

**定价与展期（增强）**
- `POST /api/pricing/licenses/extend` - 批量展期（含自动续费选项）

#### 定时任务

```python
# 每天凌晨2点：自动续费检查
schedule.every().day.at("02:00").do(run_auto_renew_check)

# 每天早上9点：续费提醒通知
schedule.every().day.at("09:00").do(run_renewal_notification_check)
```

### 10.3 使用流程

#### 场景1：启用自动续费

1. 登录用户控制台
2. 进入“授权管理”页面
3. 找到需要设置的授权码
4. 点击“启用自动续费”按钮
5. 选择续费周期（推荐3个月或6个月享受折扣）
6. 确认设置

#### 场景2：批量展期并设置自动续费

1. 在授权列表中勾选多个授权码
2. 点击“批量展期”按钮
3. 选择展期周期（如6个月）
4. 勾选“启用自动续费”选项
5. 选择自动续费周期
6. 确认支付并完成展期

#### 场景3：查看续费历史

1. 进入“授权管理”页面
2. 点击某个授权码的“查看历史”按钮
3. 查看该授权码的所有续费记录
4. 可按时间范围筛选

#### 场景4：查看统计分析

1. 进入“统计分析”页面
2. 查看概览数据（总授权码数、活跃数等）
3. 查看销售员维度的统计
4. 查看续费分析报告
5. 下载数据报表（待实现）

### 10.4 折扣机制

| 续费周期 | 折扣率 | 说明 |
|---------|--------|------|
| 1个月 | 100% | 原价 |
| 3个月 | 95% | 省5% |
| 6个月 | 90% | 省10% |
| 1年 | 80% | 省20% |

**示例计算：**
- 基础价格：100元/月
- 3个月续费：100 × 3 × 0.95 = 285元（省15元）
- 6个月续费：100 × 6 × 0.90 = 540元（省60元）
- 1年续费：100 × 12 × 0.80 = 960元（省240元）

### 10.5 部署步骤

#### 1. 执行数据库迁移

```bash
# Windows
mysql -u root -p TonjClaw < database\migrations\add_auto_renew_fields.sql
mysql -u root -p TonjClaw < database\migrations\create_renewal_history_table.sql

# Linux/Mac
mysql -u root -p TonjClaw < database/migrations/add_auto_renew_fields.sql
mysql -u root -p TonjClaw < database/migrations/create_renewal_history_table.sql
```

#### 2. 安装依赖

```bash
pip install schedule
pip install pycryptodome  # 支付宝集成时需要
```

#### 3. 重启应用

```bash
python main.py
```

观察日志输出，确认定时任务已启动：
```
定时任务调度器已启动
```

#### 4. 验证功能

- 访问 `http://localhost:5000/user-portal`
- 登录后查看授权码列表
- 测试启用自动续费功能
- 查看续费历史记录
- 访问统计分析页面

详细测试步骤请参考：`QUICK_TEST_GUIDE.md`

### 10.6 相关文档

- **功能使用说明**：`AUTO_RENEW_FEATURE.md`
- **支付宝集成指南**：`ALIPAY_INTEGRATION_GUIDE.md`
- **完整功能总结**：`FEATURES_SUMMARY.md`
- **快速测试指南**：`QUICK_TEST_GUIDE.md`

---

## 11. 风险与应对

### 9.1 技术风险

| 风险 | 等级 | 应对措施 |
|------|------|---------|
| 微信账号被封 | 高 | 使用小号;不发送消息,只接收;定期更换账号;保留企微官方备用方案 |
| Hook 失效(微信升级) | 中 | 禁止微信自动更新;准备多个版本的 Hook 驱动;建立快速降级机制(手工导入) |
| 消息丢失 | 中 | `appV2.py` 接收到后先写本地磁盘队列,再异步推 MQ;TCP服务支持ACK确认 |
| 解析错误导致订单错误 | 中 | 设置置信度阈值(默认0.7),低置信度消息进入人工审核队列;支持销售后台一键修正 |
| 服务器断电/网络中断 | 低 | 建议使用云服务器;SQLite支持本地运行;定时任务支持断点续传 |
| 前端界面不完善 | 中 | 当前仅提供API和HTML原型,完整前端需后续开发;可通过Postman/API调用使用 |

### 9.2 业务风险

| 风险 | 等级 | 应对措施 |
|------|------|---------|
| 授权码泄露 | 中 | 授权码与机器指纹+微信群ID双重绑定;异常使用监控 |
| 数据隐私 | 高 | 本地部署,数据不出内网;数据库加密(可选);定期备份 |
| 并发性能 | 低 | SQLite支持单机并发;高峰期可切换MySQL;RabbitMQ削峰填谷 |

---

## 12. 开发进展

### 12.1 V2.0 新增功能（已完成）

✅ **授权码管理增强** (2026-04-15)
- 销售员信息显示与桌面端同步
- 自动续费功能（单个/批量）
- 续费提醒通知（邮件/短信）
- 续费历史记录查询
- 统计分析功能（概览/趋势/续费分析）
- 支付宝支付集成预留

**新增文件：**
- `api/license_sync.py` - 授权码同步API
- `api/auto_renew.py` - 自动续费API
- `api/renewal_history.py` - 续费历史API
- `api/license_stats.py` - 统计分析API
- `services/auto_renew_service.py` - 自动续费服务
- `services/renewal_notification_service.py` - 续费提醒服务
- `models/user_models.py` - 添加RenewalHistory模型
- `database/migrations/add_auto_renew_fields.sql`
- `database/migrations/create_renewal_history_table.sql`

**更新文件：**
- `frontend/user-portal.html` - 用户控制台界面增强
- `services/scheduler.py` - 添加定时任务
- `api/pricing.py` - 批量展期支持自动续费
- `main.py` - 注册新蓝图和启动调度器

### 12.2 已完成模块 (90%+ 完成度)

✅ **消息接收服务** (core/appV2.py, tcp_serverV2.py)
- HTTP/TCР双协议支持
- Redis去重、RabbitMQ推送、ES存储
- ACK确认机制、心跳检测

✅ **订单管理** (services/order_service.py)
- CRUD完整实现
- 幂等性保证(order_uuid去重)
- 增量订单(加菜/减菜)
- 批量圈选(按客户/线路)
- 客户日报汇总

✅ **订单解析** (services/order_parser.py)
- jieba中文分词
- 商品匹配(精确/快捷码/模糊)
- 数量提取(斤/两/kg/箱/包)
- 备注识别(要嫩的/不要葱)
- 批量语法解析
- 增量语法解析(加5斤/减2斤)

✅ **用户认证** (services/auth_service.py)
- bcrypt密码哈希
- JWT令牌生成验证
- 登录装饰器
- 演示账号自动初始化

✅ **授权系统** (services/license_service.py)
- 授权码生成(ABC123-DEF456-GHI789格式)
- 机器指纹绑定
- 有效期管理(月付/年付)
- 离线模式支持
- 多租户隔离

✅ **机器人配置** (services/robot_service.py)
- Hook配置管理
- 启停控制
- 回复规则匹配(关键词/正则)
- 智能指令处理(报表查询/订单查询)

✅ **规则引擎** (services/rule_service.py)
- 解析规则CRUD
- 统计规则CRUD
- 优先级管理
- 规则启用/禁用

✅ **规则导入导出** (services/rule_import.py)
- CSV/TXT/MD多格式解析
- 规则预览
- 冲突检测(skip/overwrite/rename)
- 备份恢复

✅ **数据看板** (services/dashboard_service.py)
- 概览统计(总订单/总收入/活跃客户)
- 销售趋势(日/周/月)
- 商品排行榜
- 客户分布分析

✅ **报表生成** (api/reports.py)
- Excel多Sheet导出
- 按线路汇总
- 按销售汇总
- 按商品汇总

✅ **定时调度** (services/scheduler.py)
- 每日截单任务(21:30)
- 报表自动生成
- 邮件推送
- 历史消息清理

### 12.3 进行中模块 (70% 完成度)

⚠️ **云端同步** (services/cloud_sync_service.py)
- 框架已搭建
- 规则备份/恢复逻辑完成
- 需对接实际云存储(AWS S3/阿里云OSS)

⚠️ **前端界面** (frontend/)
- HTML原型完成(index.html, admin.html, user-center.html)
- 缺少Vue/React完整工程
- API已就绪,可直接对接

### 12.4 待开发模块

❌ **消息捕获引擎 DLL**
- C++实现,需注入WeChat.exe
- 拦截消息接收API
- 输出JSON格式消息
- 可使用开源方案(如wechat-hook)

❌ **完整测试套件**
- 现有单元测试覆盖率约30%
- 缺少API集成测试
- 缺少端到端测试

❌ **前端完整工程**
- 需使用Vue 3/React重构
- 订单审核页面
- 商品管理页面
- 数据看板可视化(ECharts)

### 12.5 代码质量评估

| 维度 | 评分 | 说明 |
|------|------|------|
| 后端功能完整性 | 9.5/10 | 核心业务逻辑全部实现，新增授权码管理增强 |
| 代码规范性 | 8.5/10 | 统一命名风格、完善docstring、类型提示 |
| 健壮性 | 8.5/10 | 大量异常处理、事务回滚、输入验证 |
| 可扩展性 | 9.5/10 | 插件化规则系统、多协议支持、多数据库支持 |
| 安全性 | 8.5/10 | JWT认证、bcrypt哈希、SQLAlchemy防注入 |
| 测试覆盖率 | 4.5/10 | 有基础单元测试，需补充集成测试 |
| 文档完整性 | 9/10 | 技术方案详尽，API文档完整，新增多个指南文档 |
| **综合评分** | **8.2/10** | **后端成熟度高，V2.0功能完整，需补充测试和前端** |

---

## 附录

### A. 消息解析规则示例

#### 正则规则
```python
# 匹配商品
(土豆|土)|(肉|猪肉)|(白菜)

# 匹配数量
(\d+(\.\d+)?)(斤|两|箱|包)

# 匹配备注
(要|不要|加|减)(.+?)(?=,|。|$)
```

#### jieba分词增强
```python
import jieba
jieba.add_word('土豆')  # 添加自定义词典
jieba.add_word('半斤')
words = jieba.lcut("来10斤土豆,要嫩的")
# ['来', '10', '斤', '土豆', ',', '要', '嫩', '的']
```

### B. 快捷码映射表示例

| 快捷码 | 商品名 | 默认单位 | 单价 |
|--------|--------|----------|------|
| TD | 土豆 | 斤 | 2.5 |
| R | 猪肉 | 斤 | 15.0 |
| BC | 白菜 | 斤 | 1.2 |

### C. 新增功能 API 示例

#### 授权码同步
```http
POST /api/license/sync/from-desktop
Authorization: Bearer <token>
Content-Type: application/json

{
  "licenses": [
    {
      "license_code": "ABC123-DEF456-GHI789",
      "bound_to": "group_chat_001",
      "assigned_salesperson": {
        "name": "张三",
        "phone": "13800138000",
        "wx_id": "zhangsan_wx"
      },
      "expires_at": "2026-12-31T23:59:59",
      "is_active": true
    }
  ]
}
```

#### 启用自动续费
```http
POST /api/auto-renew/enable
Authorization: Bearer <token>
Content-Type: application/json

{
  "license_id": 1,
  "renew_period": "3m"
}
```

#### 批量展期（含自动续费）
```http
POST /api/pricing/licenses/extend
Authorization: Bearer <token>
Content-Type: application/json

{
  "license_ids": [1, 2, 3],
  "period": "6m",
  "enable_auto_renew": true,
  "auto_renew_period": "6m"
}
```

#### 查询续费历史
```http
GET /api/renewal-history/list?page=1&per_page=20
Authorization: Bearer <token>
```

#### 统计分析
```http
GET /api/license-stats/overview
Authorization: Bearer <token>

Response:
{
  "success": true,
  "overview": {
    "total_licenses": 10,
    "active_licenses": 8,
    "expiring_soon": 2,
    "auto_renew_count": 5,
    "type_breakdown": {
      "monthly": 6,
      "yearly": 4
    }
  }
}
```

### D. 常见问题

**Q: Redis/RabbitMQ未安装会影响运行吗?**  
A: 不会。消息去重和队列功能会降级,核心功能仍可正常运行。建议生产环境部署完整中间件。

**Q: 如何添加新商品?**  
A: 通过 `/api/products` 接口创建,或直接修改数据库 `product` 表。

**Q: 订单解析不准确怎么办?**  
A: 检查商品的快捷码配置是否完整,可在 `data/products.json` 中添加更多同义词,或通过 `/api/rules/parse` 添加自定义解析规则。

**Q: 授权到期后会怎样?**  
A: 系统会停止处理新订单,但可查看历史数据。续费后恢复正常。

**Q: 一台服务器可以运行多个实例吗?**  
A: 可以,共享同一授权。每个实例需配置不同端口。

**Q: 如何查看日志?**  
A: 日志文件位于 `logs/` 目录下,包括 `app.log`, `tcp_server.log`, `main.log`。

**Q: 如何启用自动续费?**  
A: 登录用户控制台，在授权码列表中点击“启用自动续费”按钮，选择续费周期即可。也可在批量展期时勾选自动续费选项。

**Q: 续费提醒什么时候发送?**  
A: 系统每天上午9点检查即将过期的授权码，分别在提前30天、14天、7天、3天发送提醒通知。

**Q: 自动续费什么时候执行?**  
A: 系统每天凌晨2点检查并执行自动续费，对提前7天内过期且启用了自动续费的授权码进行续费。

**Q: 如何查看续费历史?**  
A: 在用户控制台的“授权管理”页面，点击授权码的“查看历史”按钮，或直接调用 `/api/renewal-history/list` API。

**Q: 支付宝支付何时集成?**  
A: 当前已预留支付接口和完整文档，上线前只需配置支付宝密钥即可启用。详见 `ALIPAY_INTEGRATION_GUIDE.md`。

---

## 11. VXHook 集成

### 11.1 概述
VXHook 是本系统与微信客户端通信的核心组件，负责消息的接收和发送。通过 Hook 技术，系统能够自动捕获微信群聊中的订单消息，并实现智能回复功能。

### 11.2 架构说明
```
┌─────────────┐         HTTP/TCP          ┌──────────────────┐
│  PC 微信     │ ◄──────────────────────► │  VXHook DLL      │
│  (客户端)    │   消息推送 + API调用      │  (C++ 注入模块)   │
└─────────────┘                           └────────┬─────────┘
                                                    │
                                          HTTP PUT/POST
                                                    │
                                                    ▼
┌──────────────────────────────────────────────────────────┐
│              Python Flask 应用 (端口 5000)                │
│                                                          │
│  ┌──────────────┐    ┌──────────────┐   ┌─────────────┐ │
│  │ Hook Callback│    │ Hook Client  │   │ 业务逻辑层  │ │
│  │   接口       │◄──►│  (API封装)   │◄─►│ (订单/商品) │ │
│  └──────┬───────┘    └──────────────┘   └─────────────┘ │
│         │                                               │
│         ▼                                               │
│  ┌──────────────────┐                                   │
│  │ Message Service  │                                   │
│  │ (去重/队列/存储)  │                                   │
│  └────────┬─────────┘                                   │
│           │                                             │
│           ▼                                             │
│  ┌──────────────────┐                                   │
│  │  数据库/Redis/   │                                   │
│  │  RabbitMQ/ES     │                                   │
│  └──────────────────┘                                   │
└──────────────────────────────────────────────────────────┘
```

### 11.3 核心功能
- **消息接收**: 自动捕获微信群聊和私聊消息
- **消息发送**: 支持文本、@消息、拍一拍、引用回复等多种消息类型
- **群成员管理**: 查询和管理微信群成员信息
- **语音转文本**: 将语音消息转换为文本进行处理

### 11.4 配置方法
详细配置指南请参考：[VXHook 集成指南](docs/HOOK_DEPLOYMENT.md)

主要配置文件：
- `.env`: 环境变量配置
- `config/hook_config.json`: Hook 详细配置

### 11.5 测试验证
运行测试脚本验证集成是否成功：
```bash
python test_hook_integration.py
```

### 11.6 注意事项
⚠️ **重要提醒**:
- 使用 Hook 技术可能存在账号封禁风险
- 建议仅在小号上测试，避免在主账号上使用
- 控制消息发送频率，避免触发微信风控
- 定期更新 Hook 以适配微信版本变化

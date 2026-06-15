# 项目需求文档：AI智能服务工具 (V4.0)

**文档版本**: 4.0  
**日期**: 2026年6月13日  
**项目代号**: AI-Service Pro  

---

## 1. 项目概述

### 1.1 项目背景
传统行业服务商（如旅行社、批发商、经销商等）在业务运营中面临信息碎片化、手工处理效率低、客户响应慢等痛点。本项目旨在打造一款**通用AI智能服务工具**，通过接入多种通讯平台（微信、飞书等），利用AI能力实现业务流程自动化。

### 1.2 核心目标
打造一款**面向行业服务商的AI智能服务工具**，支持多平台插件化接入，实现信息智能解析、自动响应、业务处理的全流程自动化。

**技术路线**：
- **核心**：AI智能体模块，支持多提供商（OpenAI、DeepSeek、通义千问等）
- **插件化**：通讯平台以插件形式接入（微信Hook、飞书API等）
- **行业服务**：可扩展的行业服务模块（配送管理、旅行社服务等）

### 1.3 架构定位
```
[AI智能服务平台]
    │
    ├─ [AI核心层] - AI解析、意图识别、自动回复
    │
    ├─ [通讯插件层]
    │   ├─ 微信插件 (VXHook)
    │   ├─ 飞书插件 (飞书API)
    │   └─ [可扩展更多平台]
    │
    ├─ [行业服务层]
    │   ├─ 配送管理服务 (原有)
    │   ├─ 旅行社服务 (新增)
    │   └─ [可扩展更多行业]
    │
    └─ [数据存储层] - SQLite/MySQL + Redis
```

---

## 2. 通讯插件层

### 2.1 微信插件（原有）
- 通过VXHook/sim-bot-node实现微信消息监听
- 支持群聊和私聊消息接收
- 支持文本、图片、语音等消息类型
- 支持消息自动回复、@消息、拍一拍等交互

### 2.2 飞书插件（新增）

#### 2.2.1 功能特性
- 通过飞书开放平台API实现消息监听和发送
- 支持飞书机器人消息接收（事件订阅）
- 支持飞书群聊和私聊消息发送
- 支持飞书消息卡片、@消息等交互
- 支持飞书用户信息获取和管理

#### 2.2.2 飞书API配置
- 应用凭证：App ID、App Secret
- 机器人Webhook地址
- 事件订阅地址
- 消息加密配置（可选）

#### 2.2.3 接口设计
```python
# 飞书客户端
class FeishuClient:
    def send_text(self, chat_id, text, at_user_ids=None):
        """发送文本消息"""
    
    def send_card(self, chat_id, card):
        """发送消息卡片"""
    
    def get_user_info(self, user_id):
        """获取用户信息"""
    
    def get_chat_info(self, chat_id):
        """获取群信息"""
```

---

## 3. 旅行社服务模块（新增）

### 3.1 业务场景

#### 场景1：线路信息解析与转发
- **触发**：微信/飞书收到上游发来的旅游线路推广链接
- **AI解析**：自动解析出价格、时间、成团要求、出发时间、具体线路、其他要点
- **转发**：根据设置，将线路信息转发到旅行社的旅游爱好者群

#### 场景2：群反馈自动回复与咨询
- **触发**：群友在群里反馈或提问
- **自动回复**：根据预设规则自动回复
- **咨询老板**：若无解析规则，将信息发给老板微信并咨询如何回答
- **反馈群友**：获取老板回复后，@对应群友进行回复

#### 场景3：报名处理与促单
- **触发**：收到群友报名消息
- **私聊促单**：自动私聊该群友，发送详细信息并促单
- **记录信息**：成功后自动记录报名信息到数据库

#### 场景4：定时日报
- **触发**：按设定时间自动发送
- **日报内容**：群反馈汇总、下单数、各线路统计等
- **接收对象**：老板微信/飞书

### 3.2 数据模型

#### 旅游线路表 (t_travel_route)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 线路ID |
| route_name | VARCHAR(200) | 线路名称 |
| price | DECIMAL(10,2) | 价格 |
| start_date | DATE | 出发时间 |
| group_size | INT | 成团人数要求 |
| duration | INT | 行程天数 |
| route_details | TEXT | 具体线路描述 |
| highlights | TEXT | 其他要点 |
| source_url | VARCHAR(500) | 来源链接 |
| status | VARCHAR(20) | 状态：draft/published/closed |
| created_at | DATETIME | 创建时间 |

#### 旅游群配置表 (t_travel_group)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 群ID |
| platform | VARCHAR(20) | 平台：wechat/feishu |
| group_id | VARCHAR(100) | 平台群ID |
| group_name | VARCHAR(100) | 群名称 |
| boss_wxid | VARCHAR(100) | 老板微信/飞书ID |
| is_active | TINYINT | 是否启用 |
| created_at | DATETIME | 创建时间 |

#### 报名记录表 (t_travel_registration)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 报名ID |
| route_id | BIGINT | 线路ID |
| user_id | VARCHAR(100) | 用户微信/飞书ID |
| user_name | VARCHAR(100) | 用户姓名 |
| phone | VARCHAR(20) | 联系电话 |
| status | VARCHAR(20) | 状态：pending/confirmed/payed/cancelled |
| created_at | DATETIME | 创建时间 |

#### 群反馈表 (t_travel_feedback)
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT | 反馈ID |
| group_id | BIGINT | 群ID |
| user_id | VARCHAR(100) | 用户ID |
| content | TEXT | 反馈内容 |
| response | TEXT | 回复内容 |
| status | VARCHAR(20) | 状态：pending/responded/escalated |
| created_at | DATETIME | 创建时间 |

### 3.3 API接口设计

#### 线路管理
```
POST   /api/travel/routes          # 创建线路
GET    /api/travel/routes          # 获取线路列表
GET    /api/travel/routes/<id>     # 获取线路详情
PUT    /api/travel/routes/<id>     # 更新线路
DELETE /api/travel/routes/<id>     # 删除线路
```

#### 群配置管理
```
POST   /api/travel/groups          # 创建群配置
GET    /api/travel/groups          # 获取群列表
PUT    /api/travel/groups/<id>     # 更新群配置
DELETE /api/travel/groups/<id>     # 删除群配置
```

#### 报名管理
```
POST   /api/travel/registrations   # 创建报名
GET    /api/travel/registrations   # 获取报名列表
PUT    /api/travel/registrations/<id>  # 更新报名状态
```

#### 反馈管理
```
POST   /api/travel/feedbacks       # 创建反馈
GET    /api/travel/feedbacks       # 获取反馈列表
PUT    /api/travel/feedbacks/<id>  # 回复反馈
```

#### 日报管理
```
POST   /api/travel/daily-report    # 手动触发日报
GET    /api/travel/daily-report    # 获取日报内容
```

### 3.4 旅行社服务流程

```
[上游线路信息] → [AI解析] → [线路入库] → [转发到旅游群]
                                                      │
                              [群友反馈] ←─────────────┘
                                    │
                          [匹配规则？]
                           /         \
                          是          否
                          │           │
                    [自动回复]    [咨询老板]
                          │           │
                    [反馈群友]    [老板回复]
                                       │
                              [@群友回复]

[群友报名] → [私聊促单] → [确认报名] → [记录信息]

[定时任务] → [生成日报] → [发送给老板]
```

---

## 4. AI智能体模块（增强）

### 4.1 线路信息解析
```python
def parse_travel_route(text: str, context: dict) -> dict:
    """
    输入: 旅游线路推广消息
    输出: {
        "success": true,
        "route_name": "云南大理5日游",
        "price": 1999.00,
        "start_date": "2026-07-15",
        "group_size": 10,
        "duration": 5,
        "route_details": "...",
        "highlights": ["洱海骑行", "古城夜游"],
        "confidence": 0.95
    }
    """
```

### 4.2 反馈意图识别
```python
def analyze_feedback(text: str) -> dict:
    """
    输入: 群友反馈消息
    输出: {
        "intent": "inquiry",  # inquiry/complaint/registration/other
        "route_name": "云南大理5日游",
        "question": "包含机票吗？",
        "needs_escalation": false
    }
    """
```

### 4.3 自动回复生成
```python
def generate_response(feedback: dict, rules: list) -> str:
    """根据反馈和规则生成回复内容"""
```

---

## 5. 配置说明

### 5.1 飞书配置
```env
# 飞书API配置
FEISHU_APP_ID=your-app-id
FEISHU_APP_SECRET=your-app-secret
FEISHU_BOT_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
FEISHU_EVENT_SECRET=your-event-secret
FEISHU_ENCRYPT_KEY=your-encrypt-key
FEISHU_ENABLED=false
```

### 5.2 旅行社配置
```env
# 旅行社服务配置
TRAVEL_SERVICE_ENABLED=true
TRAVEL_DAILY_REPORT_TIME=09:00
TRAVEL_AUTO_FORWARD=true
TRAVEL_AUTO_REPLY=true
```

---

## 6. 部署说明

### 6.1 飞书应用创建步骤
1. 登录飞书开放平台（https://open.feishu.cn/）
2. 创建企业自建应用
3. 配置应用凭证（App ID、App Secret）
4. 添加机器人能力
5. 配置事件订阅（消息接收）
6. 配置应用权限

### 6.2 环境变量配置
所有配置通过 `.env` 文件管理，敏感信息不进入版本库。

---

## 7. 项目交付里程碑

| 阶段 | 主要任务 | 预期产出 |
|------|----------|----------|
| **第一阶段** | 1. 更新项目需求文档<br>2. 添加飞书API配置<br>3. 创建飞书机器人客户端 | 飞书插件基础框架完成 |
| **第二阶段** | 1. 创建旅行社数据模型<br>2. 创建旅行社服务模块<br>3. 创建旅行社API接口 | 旅行社服务核心功能完成 |
| **第三阶段** | 1. 集成AI解析能力<br>2. 实现线路转发、自动回复、报名处理<br>3. 实现定时日报功能 | 旅行社服务完整功能上线 |
| **第四阶段** | 1. 测试与优化<br>2. 文档完善 | 版本发布 |

---

## 8. 注意事项

1. **飞书API权限**：确保飞书应用已获取消息发送、用户信息等必要权限
2. **消息加密**：建议启用飞书消息加密，确保数据安全
3. **AI解析准确性**：建议配置高质量的AI模型，提高线路信息解析准确率
4. **日报时间配置**：根据老板习惯配置日报发送时间
5. **多平台兼容**：确保微信和飞书插件能同时正常工作

---

## 9. 后续扩展

1. **更多通讯平台**：钉钉、企业微信等
2. **更多行业服务**：教育培训、房产中介等
3. **AI能力增强**：语音识别、图片识别、智能推荐等
4. **移动端支持**：小程序、APP等

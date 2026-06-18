# Sim.Bot 插件系统技术文档 v1.0

## 一、架构概述

插件系统采用 **动态加载 + 生命周期钩子 + 依赖管理** 架构，插件与核心系统之间通过定义的接口通信，无需修改核心代码即可扩展功能。

```
┌──────────────────────────────────────────────────────┐
│                    核心系统 (Core)                      │
│  ┌──────────┐  ┌───────────┐  ┌───────────────────┐ │
│  │ server.js │─▶│ gateway   │─▶│ PluginManager     │ │
│  │ (HTTP)    │  │ (TCP/消息) │  │ (发现/加载/生命周期)│ │
│  └──────────┘  └───────────┘  └───────┬───────────┘ │
│         │                              │             │
│         ▼                              ▼             │
│  ┌───────────────────────────────────────────────┐  │
│  │              插件层 (plugins/)                  │  │
│  │  ┌────────────┐ ┌──────────┐ ┌────────────┐  │  │
│  │  │ knowledge- │ │ membership│ │ appointment│  │  │
│  │  │ base       │ │          │ │            │  │  │
│  │  └────────────┘ └──────────┘ └────────────┘  │  │
│  │  ┌──────────────────────────────────────┐    │  │
│  │  │ industry (依赖上述三个功能插件)          │    │  │
│  │  └──────────────────────────────────────┘    │  │
│  └───────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

## 二、目录结构

```
plugins/
├── <plugin-id>/               # 插件目录名 = 插件 ID
│   ├── index.js               # 插件清单（manifest），必须 export `plugin` 对象
│   ├── store.js               # 数据访问层（可选）
│   └── routes.js              # API 路由定义（可选）
├── knowledge-base/
│   ├── index.js
│   ├── store.js
│   └── routes.js
├── membership/
│   ├── index.js
│   ├── store.js
│   └── routes.js
├── appointment/
│   ├── index.js
│   ├── store.js
│   └── routes.js
└── industry/
    ├── index.js
    ├── store.js
    └── routes.js
```

## 三、插件清单（Manifest）

每个插件必须在 `index.js` 中 `export` 一个名为 `plugin` 的对象，结构如下：

```javascript
export const plugin = {
  // ====== 必填字段 ======
  id: 'my-plugin',              // 插件唯一标识，与目录名一致
  name: 'My Plugin',            // 显示名称
  version: '1.0.0',             // 语义化版本号

  // ====== 可选字段 ======
  dependencies: [],             // 依赖的其他插件 ID 列表（默认 []）

  // ====== 生命周期钩子 ======
  lifecycle: {
    async install(db) { },     // 安装时调用（建表等一次性操作）
    async startup(ctx) { },    // 启动时调用（初始化运行时）
    async shutdown(ctx) { },   // 关闭时调用（清理资源）
  },

  // ====== API 路由 ======
  api: {
    prefix: '/admin/shop/my-plugin',   // 路由前缀，自动注册到 /api 下
    router: (ctx) => { /* 返回 express.Router */ },
  },

  // ====== 消息处理器 ======
  handlers: {
    async inboundMessage(ctx, text, wxid, nick) { /* return string|null */ },
    async bossCommand(ctx, text) { /* return string|null */ },
  },
};
```

## 四、生命周期

插件管理器按以下顺序处理每个插件：

| 阶段 | 触发时机 | 方法 | 典型用途 |
|------|---------|------|---------|
| discover | 启动时扫描 plugins/ 目录 | — | PluginManager 自动发现 |
| load | discover 后立即执行 | 动态 `import` | 加载 manifest |
| install | enable 时 | `lifecycle.install(db)` | 创建数据库表 |
| startup | install 成功后 | `lifecycle.startup(ctx)` | 初始化缓存/连接 |
| enabled | startup 成功后 | — | 开始接收消息 |
| shutdown | disable 时 | `lifecycle.shutdown(ctx)` | 释放资源 |

**ctx 上下文对象**包含：

```javascript
{
  db,             // SQLite 数据库实例
  logger,         // 日志记录器
  hookClient,     // Hook API 客户端
  config,         // 配置对象（jwtSecret, sqlitePath 等）
  pluginManager,  // 插件管理器引用
  getPlugin(id),  // 获取其他插件信息
  sendMessage(wxid, text),  // 发送消息
}
```

## 五、依赖管理

### 声明依赖

在 manifest 中声明 `dependencies` 字段：

```javascript
export const plugin = {
  id: 'industry',
  dependencies: ['knowledge-base', 'membership', 'appointment'],
  // ...
};
```

### 自动装载规则

1. **拓扑排序** — 启动时按依赖顺序加载，确保依赖先启动
2. **递归装载** — `enablePlugin()` 自动递归启用未启动的依赖
3. **反向递归** — `disablePlugin()` 会先禁用依赖当前插件的其他插件
4. **循环检测** — 检测到循环依赖时抛出错误

### 实际效果

安装 `industry` 插件时：

```
启用 industry
  → 检查依赖 [knowledge-base, membership, appointment]
  → 启用 knowledge-base（未启用则自动装载）
  → 启用 membership（未启用则自动装载）
  → 启用 appointment（未启用则自动装载）
  → 启用 industry
```

最终所有 4 个插件均处于 enabled 状态。

## 六、消息处理流水线

消息处理在 `gateway.js` 中按以下顺序执行：

### 群聊消息（Group Message）

```
收到群消息
  → 命令路由（command routing）
  → 行业话题检测（isShopRelatedMessage）
  → 各个插件的 inboundMessage handler（按依赖顺序）
     ↳ knowledge-base: 知识库匹配
     ↳ membership: 会员卡查询
     ↳ appointment: 预约查询
     ↳ industry: 服务/位置/营业信息/待提问
  → 返回回复文本（第一个非 null 回复即采用）
```

### 私聊消息（Private Message / Boss Command）

```
收到私聊消息
  → 各个插件的 bossCommand handler（按依赖顺序）
     ↳ knowledge-base: 知识库管理
     ↳ membership: 会员报表/销卡
     ↳ industry: 回答待提问
  → 返回回复文本
```

**处理器签名：**

```javascript
// inboundMessage - 处理群聊中的用户消息
async inboundMessage(ctx, text, senderWxid, senderNick) {
  // 返回 string 表示处理并回复，返回 null/undefined 表示不处理
}

// bossCommand - 处理私聊中的老板指令
async bossCommand(ctx, text) {
  // 返回 string 表示处理并回复，返回 null/undefined 表示不处理
}
```

## 七、API 路由

插件通过 `api` 字段定义 REST API 路由：

```javascript
api: {
  prefix: '/admin/shop/knowledge',   // 实际注册为 /api/admin/shop/knowledge
  router: createRouter,               // (ctx) => express.Router
}
```

路由工厂函数接收 `ctx` 上下文，返回 Express Router 实例：

```javascript
export function createRouter(ctx) {
  const router = express.Router();
  const { db } = ctx;

  router.get('/', (req, res) => {
    res.json(knowledgeStore.getAll(db, req.query));
  });

  router.post('/', (req, res) => {
    const result = knowledgeStore.create(db, req.body);
    res.json({ ok: true, ...result });
  });

  return router;
}
```

### 当前注册的路由

| 前缀 | 插件 | 功能 |
|------|------|------|
| `/api/admin/shop/knowledge` | knowledge-base | 知识库 CRUD |
| `/api/admin/shop/membership-cards` | membership | 会员卡管理 |
| `/api/admin/shop/appointments` | appointment | 预约管理 |
| `/api/admin/shop/industry` | industry | 店铺信息/服务/待提问 |

## 八、数据库设计原则

1. **表隔离** — 每个插件管理自己的表，避免跨插件写表
2. **表前缀** — 统一使用 `shop_` 前缀（如 `shop_knowledge_base`）
3. **建表时机** — 在 `lifecycle.install(db)` 中执行 `CREATE TABLE IF NOT EXISTS`
4. **跨表查询** — 尽量避免 LEFT JOIN 其他插件的表；如需引用，通过插件 API 调用而非直接 SQL
5. **数据迁移** — 插件升级时在 `startup()` 中执行 ALTER TABLE 等迁移逻辑

### 当前表归属

| 表 | 归属插件 | 说明 |
|----|---------|------|
| `shop_knowledge_base` | knowledge-base | 知识库问答 |
| `shop_membership_cards` | membership | 会员卡主表 |
| `shop_membership_usage` | membership | 会员卡使用记录 |
| `shop_appointments` | appointment | 预约记录 |
| `shop_info` | industry | 店铺基本信息 |
| `shop_services` | industry | 服务项目 |
| `shop_pending_questions` | industry | 待回答问题 |

## 九、如何创建一个新插件

### 步骤

1. **创建目录**

```
plugins/my-plugin/
├── index.js
├── store.js     （可选）
└── routes.js    （可选）
```

2. **编写 `store.js`** — 数据访问层

```javascript
export const myStore = {
  async init(db) {
    await db.exec(`CREATE TABLE IF NOT EXISTS shop_my_plugin (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )`);
  },

  getAll(db, params = {}) {
    return db.prepare(`SELECT * FROM shop_my_plugin ORDER BY id DESC`).all();
  },

  create(db, data) {
    const r = db.prepare(`INSERT INTO shop_my_plugin (name) VALUES (?)`).run(String(data.name || ''));
    return { id: r.lastInsertRowid };
  },
};
```

3. **编写 `routes.js`** — API 路由

```javascript
import express from 'express';
import { myStore } from './store.js';

export function createRouter(ctx) {
  const router = express.Router();
  const { db } = ctx;
  router.get('/', (req, res) => res.json(myStore.getAll(db)));
  router.post('/', (req, res) => res.json(myStore.create(db, req.body)));
  return router;
}
```

4. **编写 `index.js`** — 插件清单

```javascript
import { myStore } from './store.js';
import { createRouter } from './routes.js';

export const plugin = {
  id: 'my-plugin',
  name: 'My Plugin',
  version: '1.0.0',
  dependencies: [],
  lifecycle: {
    async install(db) { await myStore.init(db); },
  },
  api: {
    prefix: '/admin/shop/my-plugin',
    router: createRouter,
  },
  handlers: {
    async inboundMessage(ctx, text) {
      if (/关键字/.test(text)) return '插件回复内容';
      return null;
    },
  },
};
```

5. **重启应用** — PluginManager 自动发现并加载新插件

### 开发规范

- 插件 ID 使用 kebab-case（小写字母+连字符）
- API 路由前缀统一以 `/admin/shop/` 开头
- handler 返回 `string` 表示已处理，返回 `null` 表示不介入
- handler 内部异常需自行 catch，抛出异常会被 PluginManager 捕获并记录日志，不影响其他插件

## 十、核心集成点

### server.js

```javascript
// 初始化插件管理器
await pluginManager.initialize({
  db,           // SQLite 实例
  logger,       // 日志器
  hookClient,   // Hook 客户端
  config: { jwtSecret, publicKeyPath, sqlitePath },
  pluginManager, // 自引用
});

// 注册插件 API 路由
const pluginRoutes = pluginManager.getRoutes();
for (const { prefix, router } of pluginRoutes) {
  app.use('/api' + prefix, router);
}
```

### gateway.js

```javascript
// 获取插件的消息处理器
const handlers = pluginManager.getHandlers('inboundMessage');
for (const handler of handlers) {
  const reply = await handler(ctx, text, wxid, nick);
  if (reply) { /* 发送回复 */ break; }
}
```

## 十一、当前内置插件参考

| 插件 ID | 类型 | 依赖 | API 前缀 | 功能 |
|---------|------|------|---------|------|
| `knowledge-base` | 功能插件 | 无 | `/admin/shop/knowledge` | 知识库搜索、CRUD、自动回复 |
| `membership` | 功能插件 | 无 | `/admin/shop/membership-cards` | 会员卡办卡/销卡/统计/查询 |
| `appointment` | 功能插件 | 无 | `/admin/shop/appointments` | 预约时间槽/创建/状态流转 |
| `industry` | 行业插件 | knowledge-base, membership, appointment | `/admin/shop/industry` | 店铺信息/服务项目/待回答问题 |

## 十二、常见问题

**Q: 插件之间的依赖关系如何工作？**

插件 A 声明依赖插件 B，则 B 会在 A 之前被启动。如果 B 尚未启用，A 的启用会触发 B 的自动装载。禁用 B 时会先禁用依赖 B 的插件。

**Q: 多个插件的 handler 都会执行吗？**

会。所有插件的 handler 按依赖顺序依次执行，第一个返回非 null 文本的 handler 决定回复内容，后续 handler 不再执行。

**Q: 插件的数据表如何与核心系统隔离？**

每个插件在 `install()` 中创建自己的表，使用 `shop_` 前缀。插件之间不应直接操作对方的表，应通过插件的公开 API 交互。

**Q: 如何卸载一个插件？**

当前不支持热卸载。需从 `plugins/` 目录移除插件目录，重启应用。
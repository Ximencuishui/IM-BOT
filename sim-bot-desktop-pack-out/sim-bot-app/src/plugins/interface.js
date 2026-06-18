/**
 * Sim.Bot 插件规范 v1.0
 *
 * 插件结构：
 *   plugins/<plugin-id>/
 *     index.js    — 插件清单（manifest），必须 export 名为 `plugin` 的对象
 *     store.js    — 数据访问层（可选）
 *     routes.js   — API 路由定义（可选）
 *
 * 插件生命周期：
 *   1. discover — PluginManager 扫描 plugins/ 下每个含 index.js 的子目录
 *   2. load     — 动态 import 获取 plugin 对象
 *   3. install  — 执行 lifecycle.install(db)，一般用于建表
 *   4. startup  — 执行 lifecycle.startup(ctx)，初始化运行时
 *   5. enabled  — 加入 enabledPlugins 集合，开始接收消息
 *   6. shutdown — 执行 lifecycle.shutdown(ctx)，清理资源
 *
 * 依赖管理：
 *   - 在 manifest 中声明 dependencies: ['plugin-a', 'plugin-b']
 *   - PluginManager 按拓扑排序加载，确保依赖先启动
 *   - 启用插件时自动递归启用未启动的依赖
 *   - 禁用插件时反向递归禁用依赖该插件的插件
 *
 * 消息处理流水线（gateway.js）：
 *   group 消息: isShopRelatedMessage 过滤 → 各插件 inboundMessage handler → 回复
 *   private 消息: 各插件 bossCommand handler → 回复
 */

export const PluginInterface = {
  /** 清单版本号 */
  MANIFEST_VERSION: '1.0.0',

  /** 生命周期钩子名称 */
  LIFECYCLE_METHODS: {
    INSTALL: 'install',
    STARTUP: 'startup',
    SHUTDOWN: 'shutdown',
  },

  /** 消息处理器类型 */
  HANDLER_TYPES: {
    INBOUND_MESSAGE: 'inboundMessage',  // 群聊消息处理
    BOSS_COMMAND: 'bossCommand',         // 老板指令处理
  },

  /** API 路由前缀（统一注册在 /api 下） */
  API_PREFIX: '/admin/shop',

  /** 权限级别（预留） */
  PERMISSIONS: {
    READ: 'read',
    WRITE: 'write',
    MANAGE: 'manage',
    ADMIN: 'admin',
  },
};

/**
 * 插件清单完整结构参考（非实际导出，仅文档说明）：
 *
 * export const plugin = {
 *   id: 'my-plugin',                              // 唯一标识
 *   name: 'My Plugin',                            // 显示名称
 *   version: '1.0.0',                             // 版本号
 *   dependencies: ['knowledge-base', 'industry'],  // 依赖的其他插件 ID 列表
 *
 *   lifecycle: {
 *     async install(db) { },
 *     async startup(ctx) { },
 *     async shutdown(ctx) { },
 *   },
 *
 *   api: {
 *     prefix: '/admin/shop/my-plugin',            // 路由前缀
 *     router: (ctx) => { /* 返回 express.Router */ },
 *   },
 *
 *   handlers: {
 *     async inboundMessage(ctx, text, wxid, nick) {
 *       // ctx = { db, logger, hookClient, config, pluginManager }
 *       // return string|null
 *     },
 *     async bossCommand(ctx, text) {
 *       // ctx = { db, logger, hookClient, config, pluginManager }
 *       // return string|null
 *     },
 *   },
 * };
 */

/** 创建插件上下文对象 */
export const createPluginContext = (options) => {
  const { db, logger, auth, hookClient, config, pluginManager } = options;
  return {
    db,
    logger,
    auth,
    hookClient,
    config,
    pluginManager,

    /** 获取其他已加载的插件信息 */
    getPlugin(id) {
      return pluginManager?.getPlugin(id);
    },

    /** 获取指定类型的消息处理器列表 */
    getHandlers(type) {
      return pluginManager?.getHandlers(type) || [];
    },

    /** 发送文本消息（通过 Hook） */
    async sendMessage(wxid, message) {
      if (hookClient && typeof hookClient.sendText === 'function') {
        return hookClient.sendText(wxid, message);
      }
      throw new Error('hookClient not available');
    },
  };
};

/** 校验插件清单的完整性和必填字段 */
export const validatePluginManifest = (manifest) => {
  const errors = [];

  if (!manifest || typeof manifest !== 'object') {
    errors.push('plugin manifest must be an object');
    return { valid: false, errors };
  }

  if (!manifest.id) errors.push('plugin must have id (string)');
  if (typeof manifest.id !== 'string' && manifest.id !== undefined) errors.push('plugin.id must be a string');

  if (!manifest.name) errors.push('plugin must have name (string)');
  if (typeof manifest.name !== 'string' && manifest.name !== undefined) errors.push('plugin.name must be a string');

  if (!manifest.version) errors.push('plugin must have version (string)');

  // dependencies 必须为数组
  if (manifest.dependencies !== undefined && !Array.isArray(manifest.dependencies)) {
    errors.push('plugin.dependencies must be an array of plugin IDs');
  }

  // api 如果存在，需有 prefix 和 router
  if (manifest.api !== undefined) {
    if (!manifest.api.prefix) errors.push('plugin.api must have prefix');
    if (typeof manifest.api.router !== 'function') errors.push('plugin.api.router must be a function (ctx) => Router');
  }

  // lifecycle 方法必须为函数
  if (manifest.lifecycle !== undefined) {
    const methods = Object.values(PluginInterface.LIFECYCLE_METHODS);
    for (const method of methods) {
      if (
        manifest.lifecycle[method] !== undefined &&
        typeof manifest.lifecycle[method] !== 'function'
      ) {
        errors.push(`plugin.lifecycle.${method} must be a function`);
      }
    }
  }

  // handlers 方法必须为函数
  if (manifest.handlers !== undefined) {
    const types = Object.values(PluginInterface.HANDLER_TYPES);
    for (const type of types) {
      if (
        manifest.handlers[type] !== undefined &&
        typeof manifest.handlers[type] !== 'function'
      ) {
        errors.push(`plugin.handlers.${type} must be a function`);
      }
    }
  }

  return { valid: errors.length === 0, errors };
};

/** 当前已注册的插件列表（供参考） */
export const BUILTIN_PLUGINS = {
  KNOWLEDGE_BASE: {
    id: 'knowledge-base',
    name: 'Knowledge Base',
    dependencies: [],
    apiPrefix: '/admin/shop/knowledge',
    description: '知识库问答：支持搜索、CRUD、自动回复',
  },
  MEMBERSHIP: {
    id: 'membership',
    name: 'Membership Cards',
    dependencies: [],
    apiPrefix: '/admin/shop/membership-cards',
    description: '会员卡管理：办卡、销卡、统计、客户查询',
  },
  APPOINTMENT: {
    id: 'appointment',
    name: 'Appointment',
    dependencies: [],
    apiPrefix: '/admin/shop/appointments',
    description: '预约管理：时间槽、预约、状态流转',
  },
  INDUSTRY: {
    id: 'industry',
    name: '行业管理',
    dependencies: ['knowledge-base', 'membership', 'appointment'],
    apiPrefix: '/admin/shop/industry',
    description: '行业综合管理：店铺信息、服务项目、待回答问题',
  },
};
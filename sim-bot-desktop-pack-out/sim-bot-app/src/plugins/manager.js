import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PLUGINS_DIR = path.join(__dirname, '../../plugins');

export class PluginManager {
  constructor() {
    this.plugins = new Map();
    this.enabledPlugins = new Set();
    this.ctx = null;
    this.logger = null;
  }

  async initialize(ctx) {
    this.ctx = ctx;
    this.logger = ctx.logger;
    await this.discoverPlugins();
    await this.loadEnabledPlugins();
  }

  async discoverPlugins() {
    try {
      if (!fs.existsSync(PLUGINS_DIR)) {
        fs.mkdirSync(PLUGINS_DIR, { recursive: true });
        this.logger?.info('[plugins] 创建插件目录:', PLUGINS_DIR);
        return;
      }

      const entries = fs.readdirSync(PLUGINS_DIR, { withFileTypes: true });
      for (const entry of entries) {
        if (!entry.isDirectory()) continue;

        const pluginDir = path.join(PLUGINS_DIR, entry.name);
        const indexPath = path.join(pluginDir, 'index.js');

        if (!fs.existsSync(indexPath)) {
          this.logger?.warn('[plugins] 跳过无效插件目录:', entry.name);
          continue;
        }

        try {
          const { plugin } = await import('file://' + indexPath);
          if (!plugin || typeof plugin !== 'object') {
            this.logger?.warn('[plugins] 插件导出格式错误:', entry.name);
            continue;
          }

          this.plugins.set(plugin.id, {
            dir: pluginDir,
            manifest: plugin,
            loaded: false,
          });
          this.logger?.info('[plugins] 发现插件:', plugin.id, plugin.name,
            plugin.dependencies?.length ? `依赖: [${plugin.dependencies.join(', ')}]` : '');
        } catch (e) {
          this.logger?.error('[plugins] 加载插件失败:', entry.name, e.message);
        }
      }
    } catch (e) {
      this.logger?.error('[plugins] 发现插件失败:', e.message);
    }
  }

  /** 拓扑排序：确保依赖项先加载 */
  _getLoadOrder() {
    const ids = [...this.plugins.keys()];
    const visited = new Set();
    const result = [];

    const dfs = (id, stack) => {
      if (result.includes(id)) return;
      if (stack.has(id)) throw new Error(`循环依赖: ${[...stack, id].join(' -> ')}`);
      const info = this.plugins.get(id);
      if (!info) return;
      stack.add(id);
      const deps = info.manifest.dependencies || [];
      for (const depId of deps) {
        if (!this.plugins.has(depId)) {
          this.logger?.warn(`[plugins] 依赖「${depId}」未找到，跳过`);
          continue;
        }
        dfs(depId, stack);
      }
      stack.delete(id);
      result.push(id);
    };

    for (const id of ids) {
      dfs(id, new Set());
    }
    return result;
  }

  async loadEnabledPlugins() {
    const order = this._getLoadOrder();
    for (const id of order) {
      await this.enablePlugin(id);
    }
  }

  async enablePlugin(id) {
    const info = this.plugins.get(id);
    if (!info || this.enabledPlugins.has(id)) return;

    // 先启用依赖
    const deps = info.manifest.dependencies || [];
    for (const depId of deps) {
      if (!this.plugins.has(depId)) {
        this.logger?.warn(`[plugins] 插件「${id}」依赖「${depId}」不存在，跳过`);
        continue;
      }
      if (!this.enabledPlugins.has(depId)) {
        this.logger?.info(`[plugins] 插件「${id}」触发依赖「${depId}」自动装载`);
        await this.enablePlugin(depId);
      }
    }

    try {
      if (info.manifest.lifecycle?.install) {
        await info.manifest.lifecycle.install(this.ctx.db);
        this.logger?.info('[plugins] 安装插件:', id);
      }

      if (info.manifest.lifecycle?.startup) {
        await info.manifest.lifecycle.startup(this.ctx);
        this.logger?.info('[plugins] 启动插件:', id);
      }

      this.enabledPlugins.add(id);
      info.loaded = true;
    } catch (e) {
      this.logger?.error('[plugins] 启用插件失败:', id, e.message);
    }
  }

  async disablePlugin(id) {
    const info = this.plugins.get(id);
    if (!info || !this.enabledPlugins.has(id)) return;

    // 如果有其他插件依赖当前插件，先禁用它们
    for (const [otherId, otherInfo] of this.plugins) {
      const deps = otherInfo.manifest.dependencies || [];
      if (deps.includes(id) && this.enabledPlugins.has(otherId)) {
        await this.disablePlugin(otherId);
      }
    }

    try {
      if (info.manifest.lifecycle?.shutdown) {
        await info.manifest.lifecycle.shutdown(this.ctx);
        this.logger?.info('[plugins] 关闭插件:', id);
      }

      this.enabledPlugins.delete(id);
      info.loaded = false;
    } catch (e) {
      this.logger?.error('[plugins] 禁用插件失败:', id, e.message);
    }
  }

  getHandlers(type) {
    const handlers = [];
    for (const id of this.enabledPlugins) {
      const info = this.plugins.get(id);
      if (info?.manifest?.handlers?.[type]) {
        handlers.push(info.manifest.handlers[type]);
      }
    }
    return handlers;
  }

  getRoutes() {
    const routes = [];
    for (const id of this.enabledPlugins) {
      const info = this.plugins.get(id);
      if (info?.manifest?.api) {
        const { prefix, router } = info.manifest.api;
        if (prefix && router) {
          routes.push({ prefix, router: router(this.ctx) });
        }
      }
    }
    return routes;
  }

  getPlugin(id) {
    return this.plugins.get(id);
  }

  listPlugins() {
    const result = [];
    for (const [id, info] of this.plugins) {
      result.push({
        id,
        name: info.manifest.name,
        version: info.manifest.version,
        enabled: this.enabledPlugins.has(id),
        dependencies: info.manifest.dependencies || [],
      });
    }
    return result;
  }
}

export const pluginManager = new PluginManager();

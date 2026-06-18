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
          this.logger?.info('[plugins] 发现插件:', plugin.id, plugin.name);
        } catch (e) {
          this.logger?.error('[plugins] 加载插件失败:', entry.name, e.message);
        }
      }
    } catch (e) {
      this.logger?.error('[plugins] 发现插件失败:', e.message);
    }
  }

  async loadEnabledPlugins() {
    for (const [id, info] of this.plugins) {
      await this.enablePlugin(id);
    }
  }

  async enablePlugin(id) {
    const info = this.plugins.get(id);
    if (!info || this.enabledPlugins.has(id)) return;

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
      });
    }
    return result;
  }
}

export const pluginManager = new PluginManager();

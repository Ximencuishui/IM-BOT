# TonjClaw Web 前端项目

基于 Vue 3 + Vite + Element Plus 的现代化管理后台。

## 🚀 快速开始

### 安装依赖
```bash
pnpm install
```

### 启动开发服务器
```bash
pnpm dev
```

访问 http://localhost:5173

### 构建生产版本
```bash
pnpm build
```

### 预览生产构建
```bash
pnpm preview
```

## 📁 项目结构

```
tonjclaw-web/
├── src/
│   ├── api/              # API 接口
│   │   ├── auth.js       # 认证相关
│   │   ├── admin/        # Admin Portal API
│   │   └── desktop/      # Desktop App API
│   ├── assets/           # 静态资源
│   ├── components/       # 通用组件
│   ├── layouts/          # 布局组件
│   │   ├── AdminLayout.vue    # Admin 布局
│   │   └── DesktopLayout.vue  # Desktop 布局
│   ├── router/           # 路由配置
│   │   └── index.js      # 路由定义
│   ├── stores/           # 状态管理 (Pinia)
│   │   └── user.js       # 用户状态
│   ├── utils/            # 工具函数
│   │   └── request.js    # Axios 封装
│   ├── views/            # 页面组件
│   │   ├── Login.vue     # 登录页
│   │   ├── admin/        # Admin Portal 页面
│   │   │   ├── Dashboard.vue
│   │   │   ├── Users/
│   │   │   ├── Licenses/
│   │   │   └── ...
│   │   └── desktop/      # Desktop App 页面
│   │       ├── Dashboard.vue
│   │       ├── Orders/
│   │       ├── Products/
│   │       └── ...
│   ├── App.vue           # 根组件
│   └── main.js           # 入口文件
├── .env.development      # 开发环境变量
├── .env.production       # 生产环境变量
├── index.html
├── package.json
└── vite.config.js
```

## 🎯 技术栈

- **框架**: Vue 3.5+
- **构建工具**: Vite 8.x
- **UI 库**: Element Plus 2.x
- **路由**: Vue Router 4.x
- **状态管理**: Pinia 2.x
- **HTTP 客户端**: Axios 1.x
- **图表**: ECharts 5.x
- **CSS 预处理器**: SCSS
- **包管理器**: pnpm

## 🔧 配置说明

### 环境变量

`.env.development`:
```env
VITE_API_BASE_URL=http://localhost:5000
```

`.env.production`:
```env
VITE_API_BASE_URL=https://api.yourdomain.com
```

### API 基础路径

在 `src/utils/request.js` 中配置 axios 实例。

## 📝 开发规范

### 组件命名
- 文件名：PascalCase（如 `UserList.vue`）
- 组件名：与文件名一致

### 目录结构
- 按功能模块组织
- 每个模块包含 `index.vue` 作为入口

### 代码风格
- 使用 Composition API (`<script setup>`)
- 遵循 ESLint + Prettier 规则

## 🔄 迁移进度

### Phase 1: 基础设施 ✅
- [x] 项目初始化
- [x] Element Plus 配置
- [x] 路由配置
- [x] 状态管理
- [x] API 封装
- [x] 布局组件
- [x] 登录页面

### Phase 2: Admin Portal 核心功能 🚧
- [x] Dashboard（数据概览）
- [ ] 用户管理
- [ ] 授权码管理
- [ ] 定价配置
- [ ] 系统设置

### Phase 3: Admin Portal 高级功能 ⏳
- [ ] 规则库管理
- [ ] 订单与续费
- [ ] 推广管理
- [ ] 系统监控
- [ ] 审计日志

### Phase 4: Desktop App 迁移 ⏳
- [ ] 订单管理
- [ ] 商品管理
- [ ] 客户管理
- [ ] 机器人配置
- [ ] 报表统计
- [ ] 规则配置
- [ ] 线路产品

## 🐛 常见问题

### 1. 端口被占用
修改 `vite.config.js`:
```js
export default defineConfig({
  server: {
    port: 5174  // 更改端口
  }
})
```

### 2. API 请求失败
检查 `.env.development` 中的 `VITE_API_BASE_URL` 是否正确。

### 3. 样式不生效
确保使用了 `<style scoped>` 或正确的 CSS 选择器。

## 📚 相关文档

- [Vue 3 文档](https://vuejs.org/)
- [Vite 文档](https://vitejs.dev/)
- [Element Plus 文档](https://element-plus.org/)
- [Pinia 文档](https://pinia.vuejs.org/)
- [前端重构计划](../../docs/FRONTEND_REFACTORING_PLAN.md)
- [Admin Portal 需求](../../docs/ADMIN_PORTAL_REQUIREMENTS.md)

## 📞 技术支持

如有问题，请联系开发团队。

---

**最后更新**: 2026-04-16
**版本**: v0.1.0

import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import router from './router'
import { createPinia } from 'pinia'
import App from './App.vue'
import './styles/theme.scss'

const app = createApp(App)

// 按需注册常用图标，减少全局注册开销
const commonIcons = ['ChatDotRound', 'Search', 'ArrowDown', 'ArrowUp', 'Delete', 'Edit', 'Plus', 'Refresh', 'Setting', 'User', 'Menu', 'Close']
for (const key of commonIcons) {
  if (ElementPlusIconsVue[key]) {
    app.component(key, ElementPlusIconsVue[key])
  }
}

app.use(ElementPlus, { locale: zhCn })
app.use(createPinia())
app.use(router)
app.mount('#app')

<template>
  <el-container class="desktop-layout desktop-soft-root">
    <el-aside :width="sidebarWidth" class="sidebar">
      <div class="sidebar-brand" @click="goToUserCenter">
        <span class="sidebar-logo-mark">T</span>
        <div v-if="!sidebarCollapsed" class="sidebar-product">
          <strong>TonjClaw</strong>
          <span>本地订货控制台</span>
        </div>
      </div>

      <nav class="sidebar-nav">
        <router-link
          v-for="item in navItems"
          :key="item.path + (item.query?.tab || '')"
          :to="item.query ? { path: item.path, query: item.query } : item.path"
          class="nav-item"
          :class="{ 'nav-item--active': isNavActive(item) }"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span v-if="!sidebarCollapsed">{{ item.title }}</span>
        </router-link>
      </nav>

      <div class="sidebar-spacer" />

      <div v-if="!sidebarCollapsed" class="sidebar-card">
        <p>消息经 Hook 回调至本机服务，数据保存在本地。</p>
      </div>

      <button type="button" class="sidebar-collapse" @click="toggleSidebar" :title="sidebarCollapsed ? '展开' : '收起'">
        <el-icon>
          <component :is="sidebarCollapsed ? Expand : Fold" />
        </el-icon>
      </button>
    </el-aside>

    <el-container class="main-column">
      <DesktopHookStatusBar />
      <el-header class="header">
        <el-breadcrumb separator="/">
          <el-breadcrumb-item :to="{ path: '/desktop/dashboard' }">首页</el-breadcrumb-item>
          <el-breadcrumb-item>{{ currentTitle }}</el-breadcrumb-item>
        </el-breadcrumb>
        <el-dropdown @command="handleCommand">
          <span class="user-info">
            <el-avatar :size="32" class="user-avatar">
              {{ userInfo.username?.charAt(0)?.toUpperCase() }}
            </el-avatar>
            <span v-if="!sidebarCollapsed" class="username">{{ userInfo.username }}</span>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">用户中心</el-dropdown-item>
              <el-dropdown-item command="switch-admin" divided>管理后台</el-dropdown-item>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>

      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '../stores/user'
import { ElMessageBox } from 'element-plus'
import DesktopHookStatusBar from '../components/desktop/DesktopHookStatusBar.vue'
import { maybeShowDemoBossTrialDialog } from '../utils/demoBossTrial'
import '../styles/desktop-soft.scss'
import {
  DataLine,
  Document,
  Goods,
  UserFilled,
  User,
  ChatDotRound,
  ChatLineRound,
  TrendCharts,
  CollectionTag,
  Connection,
  Key,
  Setting,
  ArrowDown,
  Expand,
  Fold
} from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

const navItems = [
  { path: '/desktop/dashboard', title: '数据概览', icon: DataLine },
  { path: '/desktop/orders', title: '订单管理', icon: Document },
  { path: '/desktop/products', title: '商品管理', icon: Goods },
  { path: '/desktop/salespersons', title: '销售人员', icon: UserFilled },
  { path: '/desktop/customers', title: '客户管理', icon: User },
  { path: '/desktop/groups', title: '群管理', icon: ChatLineRound },
  { path: '/desktop/licenses', title: '授权码', icon: Key },
  { path: '/desktop/robot', title: '机器人运行', icon: ChatDotRound },
  { path: '/desktop/reports', title: '报表统计', icon: TrendCharts },
  { path: '/desktop/rules', title: '规则配置', icon: CollectionTag },
  { path: '/desktop/routes', title: '线路管理', icon: Connection },
  { path: '/desktop/robot', title: '主程序续费', icon: Key, query: { tab: 'renewal' } },
  { path: '/desktop/groups', title: '群续期', icon: Key, query: { tab: 'renew' } },
  { path: '/desktop/ops', title: '系统运维', icon: Setting }
]

const userInfo = computed(() => userStore.userInfo)
const activeMenu = computed(() => route.path)

function isNavActive(item) {
  if (route.path !== item.path) return false
  if (item.query?.tab) return route.query.tab === item.query.tab
  if (item.path === '/desktop/robot') {
    return route.query.tab !== 'renewal'
  }
  if (item.path === '/desktop/groups') {
    return !item.query?.tab || item.query.tab === 'list'
  }
  return true
}
const currentTitle = computed(() => route.meta.title || '')
const sidebarCollapsed = computed(() => userStore.sidebarCollapsed)
const sidebarWidth = computed(() => (sidebarCollapsed.value ? '72px' : 'var(--sidebar-width, 240px)'))

const toggleSidebar = () => {
  userStore.toggleSidebar()
}

const handleCommand = (command) => {
  if (command === 'logout') {
    ElMessageBox.confirm('确定要退出登录吗?', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }).then(() => {
      userStore.logout()
      router.push('/login')
    })
  } else if (command === 'profile') {
    router.push('/user/dashboard')
  } else if (command === 'switch-admin') {
    router.push('/admin/dashboard')
  }
}

const goToUserCenter = () => {
  router.push('/user/dashboard')
}

onMounted(() => {
  maybeShowDemoBossTrialDialog(userInfo.value).catch(() => {})
})
</script>

<style scoped lang="scss">
.desktop-layout {
  height: 100vh;
  background: var(--bg-app, #f0f2f5);
}

.sidebar {
  background: var(--bg-sidebar, #fff);
  box-shadow: 4px 0 24px rgba(15, 23, 42, 0.04);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: width 0.25s ease;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 18px 16px;
  cursor: pointer;
  border-bottom: 1px solid var(--border, rgba(15, 23, 42, 0.06));

  &:hover {
    background: #fafbfc;
  }
}

.sidebar-logo-mark {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: linear-gradient(135deg, #5b4ae8 0%, #8b5cf6 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 18px;
  flex-shrink: 0;
}

.sidebar-product {
  display: flex;
  flex-direction: column;
  min-width: 0;

  strong {
    font-size: 15px;
    color: var(--text, #1e293b);
  }

  span {
    font-size: 11px;
    color: var(--text-muted, #94a3b8);
  }
}

.sidebar-nav {
  flex: 1;
  padding: 8px 10px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  color: var(--text-secondary, #64748b);
  text-decoration: none;
  font-size: 14px;
  border: none;
  border-left: 3px solid transparent;
  transition: background 0.15s, color 0.15s;

  &:hover {
    background: #f8fafc;
    color: var(--text, #1e293b);
  }

  &--active {
    background: var(--accent-subtle, rgba(91, 74, 232, 0.1));
    color: var(--brand-primary, #5b4ae8);
    border-left-color: var(--brand-primary, #5b4ae8);
    font-weight: 600;
  }
}

.sidebar-spacer {
  flex: 0;
}

.sidebar-card {
  margin: 8px 12px 12px;
  padding: 12px;
  border-radius: 12px;
  background: linear-gradient(135deg, rgba(91, 74, 232, 0.08), rgba(13, 148, 136, 0.08));
  font-size: 12px;
  color: var(--text-secondary, #64748b);
  line-height: 1.5;

  p {
    margin: 0;
  }
}

.sidebar-collapse {
  margin: 0 12px 16px;
  padding: 8px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: #f8fafc;
  cursor: pointer;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;

  &:hover {
    background: var(--accent-subtle);
    color: var(--brand-primary);
  }
}

.main-column {
  flex-direction: column;
  min-width: 0;
}

.header {
  height: 48px;
  background: #fff;
  border-bottom: 1px solid var(--border);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 8px;

  &:hover {
    background: #f1f5f9;
  }
}

.user-avatar {
  background: var(--brand-primary, #5b4ae8) !important;
}

.username {
  font-size: 14px;
  color: var(--text-secondary);
}

.main-content {
  background: var(--bg-app, #f0f2f5);
  padding: 20px;
  overflow-y: auto;
}
</style>

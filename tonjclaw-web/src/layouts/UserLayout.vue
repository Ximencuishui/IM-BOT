<template>
  <el-container class="user-layout">
    <el-header class="header">
      <div class="header-left">
        <router-link to="/user/dashboard" class="logo">
          <img src="/image/logo.png" alt="TonjClaw Logo" style="height: 40px; margin-right: 10px;" />
          <span>TonjClaw</span>
        </router-link>
      </div>
      <div class="header-right">
        <el-dropdown @command="handleCommand">
          <span class="user-info">
            <el-avatar :size="32" style="background-color: #3b82f6">
              {{ userInfo.username?.charAt(0)?.toUpperCase() }}
            </el-avatar>
            <span class="username">{{ userInfo.username }}</span>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="switch-desktop">切换到桌面端</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>
    
    <el-container class="body-container">
      <el-aside width="220px" class="sidebar">
        <el-menu
          :default-active="activeMenu"
          router
          background-color="#ffffff"
          text-color="#606266"
          active-text-color="#409EFF"
        >
          <el-menu-item index="/user/dashboard">
            <el-icon><HomeFilled /></el-icon>
            <span>首页概览</span>
          </el-menu-item>
          <el-menu-item index="/user/profile">
            <el-icon><User /></el-icon>
            <span>个人信息</span>
          </el-menu-item>
          <el-menu-item index="/user/licenses">
            <el-icon><Key /></el-icon>
            <span>授权管理</span>
          </el-menu-item>
          <el-menu-item index="/user/subscriptions">
            <el-icon><CreditCard /></el-icon>
            <span>订阅管理</span>
          </el-menu-item>
          <el-menu-item index="/user/rules">
            <el-icon><Document /></el-icon>
            <span>规则备份</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { ArrowDown, HomeFilled, User, Key, CreditCard, Document } from '@element-plus/icons-vue'
import { useUserStore } from '../stores/user'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const userInfo = computed(() => userStore.userInfo || {})
const activeMenu = computed(() => route.path)

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
  } else if (command === 'switch-desktop') {
    router.push('/desktop/orders')
  }
}
</script>

<style scoped lang="scss">
.user-layout {
  height: 100vh;
  background-color: #f1f5f9;
  display: flex;
  flex-direction: column;
  
  .header {
    background-color: #fff;
    border-bottom: 1px solid #e2e8f0;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 24px;
    height: 60px;
    
    .header-left {
      .logo {
        display: flex;
        align-items: center;
        text-decoration: none;
        transition: opacity 0.3s ease;
        
        &:hover {
          opacity: 0.8;
        }
        
        img {
          max-height: 40px;
          width: auto;
          object-fit: contain;
        }
        
        span {
          font-size: 20px;
          color: #1e293b;
          font-weight: bold;
        }
      }
    }
    
    .header-right {
      .user-info {
        display: flex;
        align-items: center;
        gap: 8px;
        cursor: pointer;
        padding: 8px 12px;
        border-radius: 8px;
        transition: background-color 0.3s ease;
        
        &:hover {
          background-color: #f1f5f9;
        }
        
        .username {
          font-size: 14px;
          color: #1e293b;
        }
      }
    }
  }
  
  .body-container {
    flex: 1;
    overflow: hidden;
    
    .sidebar {
      background-color: #fff;
      border-right: 1px solid #e2e8f0;
      
      ::deep(.el-menu) {
        border-right: none;
      }
    }
    
    .main-content {
      padding: 24px;
      overflow-y: auto;
      background-color: #f1f5f9;
    }
  }
}
</style>

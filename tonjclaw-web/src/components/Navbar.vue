<template>
  <nav class="navbar">
    <div class="nav-container">
      <router-link to="/" class="nav-logo">
        <span class="logo-text">AI <span class="logo-highlight">IMBot</span></span>
      </router-link>
      <div class="nav-links">
        <router-link to="/" class="nav-link" :class="{ active: $route.name === 'Home' }">首页</router-link>
        <router-link to="/industry-cases" class="nav-link" :class="{ active: $route.name === 'IndustryCases' }">行业案例</router-link>
        <router-link to="/plugin-store" class="nav-link" :class="{ active: $route.name === 'PluginStore' }">插件商店</router-link>
        <router-link to="/commercial-im" class="nav-link" :class="{ active: $route.name === 'CommercialIM' }">商用IM</router-link>
      </div>
      <div class="nav-actions">
        <el-button text @click="goToLogin">登录</el-button>
        <el-button type="primary" @click="goToLogin">免费试用</el-button>
      </div>
      <div class="mobile-menu-btn" @click="toggleMobileMenu">
        <el-icon><Menu /></el-icon>
      </div>
    </div>
    <div class="mobile-menu" :class="{ active: mobileMenuOpen }">
      <router-link to="/" class="mobile-nav-link" @click="closeMobileMenu">首页</router-link>
      <router-link to="/industry-cases" class="mobile-nav-link" @click="closeMobileMenu">行业案例</router-link>
      <router-link to="/plugin-store" class="mobile-nav-link" @click="closeMobileMenu">插件商店</router-link>
      <router-link to="/commercial-im" class="mobile-nav-link" @click="closeMobileMenu">商用IM</router-link>
      <div class="mobile-actions">
        <el-button text @click="goToLogin">登录</el-button>
        <el-button type="primary" @click="goToLogin">免费试用</el-button>
      </div>
    </div>
    <div class="mobile-menu-overlay" v-if="mobileMenuOpen" @click="closeMobileMenu"></div>
  </nav>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Menu } from '@element-plus/icons-vue'

const router = useRouter()
const mobileMenuOpen = ref(false)

const goToLogin = () => {
  router.push('/login')
}

const toggleMobileMenu = () => {
  mobileMenuOpen.value = !mobileMenuOpen.value
}

const closeMobileMenu = () => {
  mobileMenuOpen.value = false
}
</script>

<style scoped>
.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: rgba(15, 23, 42, 0.95);
  backdrop-filter: blur(12px);
  padding: 14px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.nav-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 30px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.nav-logo {
  text-decoration: none;
}

.nav-logo .logo-text {
  font-size: 24px;
  font-weight: 800;
  color: #fff;
}

.nav-logo .logo-highlight {
  background: linear-gradient(135deg, #818cf8 0%, #c084fc 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.nav-links {
  display: flex;
  gap: 32px;
}

.nav-link {
  color: #e2e8f0;
  text-decoration: none;
  font-size: 15px;
  font-weight: 500;
  transition: color 0.25s;
}

.nav-link:hover,
.nav-link.active {
  color: #a5b4fc;
}

.nav-actions {
  display: flex;
  gap: 12px;
}

.mobile-menu-btn {
  display: none;
  color: #fff;
  font-size: 24px;
  cursor: pointer;
}

.mobile-menu {
  display: none;
  position: fixed;
  top: 70px;
  left: 0;
  right: 0;
  background: rgba(15, 23, 42, 0.98);
  backdrop-filter: blur(12px);
  padding: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  transform: translateY(-100%);
  transition: transform 0.3s ease;
}

.mobile-menu.active {
  transform: translateY(0);
}

.mobile-nav-link {
  display: block;
  color: #e2e8f0;
  text-decoration: none;
  font-size: 16px;
  font-weight: 500;
  padding: 14px 20px;
  border-radius: 12px;
  margin-bottom: 8px;
  transition: all 0.25s;
}

.mobile-nav-link:hover {
  color: #a5b4fc;
  background: rgba(255, 255, 255, 0.05);
}

.mobile-actions {
  display: flex;
  gap: 12px;
  padding: 20px;
  margin-top: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.mobile-menu-overlay {
  position: fixed;
  top: 70px;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 999;
}

@media (max-width: 768px) {
  .nav-links {
    display: none;
  }
  
  .nav-actions {
    display: none;
  }
  
  .mobile-menu-btn {
    display: block;
  }
  
  .mobile-menu {
    display: block;
  }
}
</style>
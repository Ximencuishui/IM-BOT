import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'
import desktopRoutes from './desktop'

const routes = [
  {
    path: '/',
    redirect: '/user/dashboard'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false }
  },
  // 用户中心路由
  {
    path: '/user',
    component: () => import('../layouts/UserLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'UserDashboard',
        component: () => import('../views/user/Dashboard/index.vue'),
        meta: { title: '用户中心' }
      },
      {
        path: 'profile',
        name: 'UserProfile',
        component: () => import('../views/user/Profile/index.vue'),
        meta: { title: '个人信息' }
      },
      {
        path: 'licenses',
        name: 'UserLicenses',
        component: () => import('../views/user/Licenses/index.vue'),
        meta: { title: '授权管理' }
      },
      {
        path: 'subscriptions',
        name: 'UserSubscriptions',
        component: () => import('../views/user/Subscriptions/index.vue'),
        meta: { title: '订阅管理' }
      },
      {
        path: 'rules',
        name: 'UserRules',
        component: () => import('../views/user/Rules/index.vue'),
        meta: { title: '规则备份' }
      }
    ]
  },
  ...desktopRoutes,
  {
    path: '/admin',
    component: () => import('../layouts/AdminLayout.vue'),
    meta: { requiresAuth: true, role: 'admin' },
    children: [
      {
        path: 'dashboard',
        name: 'AdminDashboard',
        component: () => import('../views/admin/Dashboard.vue'),
        meta: { title: '数据概览' }
      },
      {
        path: 'users',
        name: 'AdminUsers',
        component: () => import('../views/admin/Users/index.vue'),
        meta: { title: '用户管理' }
      },
      {
        path: 'licenses',
        name: 'AdminLicenses',
        component: () => import('../views/admin/Licenses/index.vue'),
        meta: { title: '授权码管理' }
      },
      {
        path: 'pricing',
        name: 'AdminPricing',
        component: () => import('../views/admin/Pricing/index.vue'),
        meta: { title: '定价配置' }
      },
      {
        path: 'rules',
        name: 'AdminRules',
        component: () => import('../views/admin/Rules/index.vue'),
        meta: { title: '规则库管理' }
      },
      {
        path: 'orders',
        name: 'AdminOrders',
        component: () => import('../views/admin/Orders/index.vue'),
        meta: { title: '订单与续费' }
      },
      {
        path: 'affiliates',
        name: 'AdminAffiliates',
        component: () => import('../views/admin/Affiliates/index.vue'),
        meta: { title: '推广管理' }
      },
      {
        path: 'monitoring',
        name: 'AdminMonitoring',
        component: () => import('../views/admin/Monitoring/index.vue'),
        meta: { title: '系统监控' }
      },
      {
        path: 'audit-logs',
        name: 'AdminAuditLogs',
        component: () => import('../views/admin/AuditLogs/index.vue'),
        meta: { title: '审计日志' }
      },
      {
        path: 'settings',
        name: 'AdminSettings',
        component: () => import('../views/admin/Settings/index.vue'),
        meta: { title: '系统设置' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

function loadStoredUserInfo() {
  try {
    return JSON.parse(localStorage.getItem('userInfo') || '{}')
  } catch {
    localStorage.removeItem('userInfo')
    return {}
  }
}

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  const userInfo = loadStoredUserInfo()
  
  if (to.meta.requiresAuth && !token) {
    // 需要认证但未登录，跳转到登录页
    next('/login')
  } else if (to.path === '/login' && token) {
    // 已登录，根据角色跳转
    const role = userInfo.role
    if (role === 'super_admin' || role === 'admin') {
      next('/admin/dashboard')
    } else {
      next('/user/dashboard')
    }
  } else if (to.meta.role) {
    // 更灵活的角色校验
    const requiredRole = to.meta.role;
    const userRole = userInfo.role;
    
    // 如果要求的是admin或super_admin，允许两者都访问
    if ((requiredRole === 'admin' || requiredRole === 'super_admin') && 
        (userRole === 'admin' || userRole === 'super_admin')) {
      next();
      return;
    }
    
    // 其他情况严格匹配角色
    if (userRole !== requiredRole) {
      ElMessage.warning('您没有权限访问该页面');
      next('/user/dashboard');
      return;
    }
  } else {
    // 正常访问
    next()
  }
})

export default router

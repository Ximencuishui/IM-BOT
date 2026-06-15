<template>
  <div class="user-dashboard">
    <!-- 欢迎卡片 -->
    <el-card class="welcome-card">
      <div class="welcome-content">
        <div>
          <h2>欢迎回来，{{ userInfo.username }}</h2>
          <p class="subtitle">今天是{{ currentDate }}，祝您工作顺利！</p>
        </div>
        <el-button type="primary" @click="goToDesktop">
          <el-icon><ArrowRight /></el-icon>
          进入桌面端
        </el-button>
      </div>
    </el-card>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-cards">
      <el-col :xs="24" :sm="12" :md="8">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-item">
            <div class="stat-icon" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%)">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ stats.orderCount }}</div>
              <div class="stat-label">我的订单</div>
              <div class="stat-trend">本月 {{ stats.monthOrders }} 单</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :sm="12" :md="8">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-item">
            <div class="stat-icon" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%)">
              <el-icon><CreditCard /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ stats.licenseCount }}</div>
              <div class="stat-label">授权数</div>
              <div class="stat-trend" :class="{ 'expiring': stats.isExpiring }">
                {{ stats.licenseStatus }}
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :sm="12" :md="8">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-item">
            <div class="stat-icon" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)">
              <el-icon><Calendar /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ stats.daysRemaining }}</div>
              <div class="stat-label">剩余天数</div>
              <div class="stat-trend">到期: {{ stats.expireDate }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <!-- 快捷操作 -->
      <el-col :xs="24" :md="12">
        <el-card class="quick-actions-card">
          <template #header>
            <div class="card-header">
              <span>快捷操作</span>
            </div>
          </template>
          <div class="action-grid">
            <div class="action-item" @click="goToDesktop">
              <div class="action-icon" style="background-color: #3b82f6">
                <el-icon><Monitor /></el-icon>
              </div>
              <span>桌面端</span>
            </div>
            <div class="action-item" @click="viewOrders">
              <div class="action-icon" style="background-color: #10b981">
                <el-icon><List /></el-icon>
              </div>
              <span>查看订单</span>
            </div>
            <div class="action-item" @click="viewLicenses">
              <div class="action-icon" style="background-color: #f59e0b">
                <el-icon><Key /></el-icon>
              </div>
              <span>授权管理</span>
            </div>
            <div class="action-item" @click="viewProfile">
              <div class="action-icon" style="background-color: #ef4444">
                <el-icon><User /></el-icon>
              </div>
              <span>个人信息</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 最近订单 -->
      <el-col :xs="24" :md="12">
        <el-card class="recent-orders-card">
          <template #header>
            <div class="card-header">
              <span>最近订单</span>
              <el-button link type="primary" @click="viewAllOrders">查看全部</el-button>
            </div>
          </template>
          <el-empty v-if="recentOrders.length === 0" description="暂无订单" :image-size="80" />
          <div v-else class="order-list">
            <div v-for="order in recentOrders" :key="order.id" class="order-item">
              <div class="order-info">
                <div class="order-date">{{ order.date }}</div>
                <div class="order-amount">¥{{ order.amount }}</div>
              </div>
              <el-tag :type="getStatusType(order.status)" size="small">
                {{ getStatusText(order.status) }}
              </el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 个人信息 -->
    <el-card class="info-card">
      <template #header>
        <div class="card-header">
          <span>个人信息</span>
          <el-button link type="primary" @click="editProfile">编辑</el-button>
        </div>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="用户名">
          <el-icon><User /></el-icon>
          {{ userInfo.username }}
        </el-descriptions-item>
        <el-descriptions-item label="角色">
          <el-tag :type="getRoleType(userInfo.role)">{{ userInfo.role }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="邮箱">
          <el-icon><Message /></el-icon>
          {{ userInfo.email || '未设置' }}
        </el-descriptions-item>
        <el-descriptions-item label="手机号">
          <el-icon><Phone /></el-icon>
          {{ userInfo.phone || '未设置' }}
        </el-descriptions-item>
        <el-descriptions-item label="注册时间" :span="2">
          <el-icon><Clock /></el-icon>
          {{ userInfo.created_at || '-' }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Document, CreditCard, Calendar, ArrowRight, Monitor, List,
  Key, User, Message, Phone, Clock
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()
const userInfo = computed(() => userStore.userInfo || {})

// 当前日期
const currentDate = computed(() => {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  const weekDays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
  const weekDay = weekDays[now.getDay()]
  return `${year}年${month}月${day}日 ${weekDay}`
})

// 统计数据
const stats = ref({
  orderCount: 0,
  monthOrders: 0,
  licenseCount: 0,
  licenseStatus: '未激活',
  isExpiring: false,
  daysRemaining: '-',
  expireDate: '-'
})

// 最近订�?
const recentOrders = ref([])

// 加载数据
const loadDashboardData = async () => {
  try {
    // TODO: 调用后端 API 获取真实数据
    // 模拟数据
    stats.value = {
      orderCount: 128,
      monthOrders: 23,
      licenseCount: 2,
      licenseStatus: '正常',
      isExpiring: false,
      daysRemaining: 365,
      expireDate: '2027-04-17'
    }
    
    recentOrders.value = [
      { id: 1, date: '2026-04-17', amount: 156.50, status: 'completed' },
      { id: 2, date: '2026-04-16', amount: 89.00, status: 'pending' },
      { id: 3, date: '2026-04-15', amount: 234.80, status: 'completed' }
    ]
  } catch (error) {
    console.error('加载仪表盘数据失�?', error)
  }
}

// 快捷操作
const goToDesktop = () => {
  router.push('/desktop/orders')
}

const viewOrders = () => {
  router.push('/desktop/orders')
}

const viewLicenses = () => {
  ElMessage.info('授权管理功能开发中')
}

const viewProfile = () => {
  ElMessage.info('个人信息编辑功能开发中')
}

const editProfile = () => {
  ElMessage.info('个人信息编辑功能开发中')
}

const viewAllOrders = () => {
  router.push('/desktop/orders')
}

// 工具函数
const getStatusType = (status) => {
  const map = {
    completed: 'success',
    pending: 'warning',
    cancelled: 'danger'
  }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = {
    completed: '已完成',
    pending: '待处理',
    cancelled: '已取消'
  }
  return map[status] || status
}

const getRoleType = (role) => {
  const map = {
    admin: 'danger',
    user: 'primary',
    vip: 'warning'
  }
  return map[role] || 'info'
}

onMounted(() => {
  loadDashboardData()
})
</script>

<style scoped lang="scss">
.user-dashboard {
  .welcome-card {
    margin-bottom: 20px;
    
    .welcome-content {
      display: flex;
      justify-content: space-between;
      align-items: center;
      
      h2 {
        margin: 0 0 8px 0;
        color: #1e293b;
        font-size: 24px;
      }
      
      .subtitle {
        margin: 0;
        color: #64748b;
        font-size: 14px;
      }
    }
  }

  .stats-cards {
    margin-bottom: 20px;
    
    .stat-card {
      transition: transform 0.3s ease, box-shadow 0.3s ease;
      
      &:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
      }
    }
    
    .stat-item {
      display: flex;
      align-items: center;
      gap: 16px;
      
      .stat-icon {
        width: 56px;
        height: 56px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #fff;
        font-size: 28px;
        flex-shrink: 0;
      }
      
      .stat-content {
        flex: 1;
        
        .stat-value {
          font-size: 28px;
          font-weight: bold;
          color: #1e293b;
          line-height: 1;
        }
        
        .stat-label {
          font-size: 14px;
          color: #64748b;
          margin-top: 8px;
        }
        
        .stat-trend {
          font-size: 12px;
          color: #10b981;
          margin-top: 4px;
          
          &.expiring {
            color: #ef4444;
          }
        }
      }
    }
  }

  .quick-actions-card,
  .recent-orders-card {
    margin-bottom: 20px;
    
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-weight: bold;
      color: #1e293b;
    }
  }
  
  .action-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
    
    .action-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      padding: 16px;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.3s ease;
      background-color: #f8fafc;
      
      &:hover {
        background-color: #e2e8f0;
        transform: translateY(-2px);
      }
      
      .action-icon {
        width: 48px;
        height: 48px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #fff;
        font-size: 24px;
      }
      
      span {
        font-size: 14px;
        color: #475569;
        font-weight: 500;
      }
    }
  }
  
  .order-list {
    .order-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 0;
      border-bottom: 1px solid #e2e8f0;
      
      &:last-child {
        border-bottom: none;
      }
      
      .order-info {
        flex: 1;
        
        .order-date {
          font-size: 14px;
          color: #64748b;
          margin-bottom: 4px;
        }
        
        .order-amount {
          font-size: 16px;
          font-weight: bold;
          color: #1e293b;
        }
      }
    }
  }

  .info-card {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-weight: bold;
      color: #1e293b;
    }
    
    ::deep(.el-descriptions__label) {
      display: flex;
      align-items: center;
      gap: 4px;
    }
  }
}
</style>

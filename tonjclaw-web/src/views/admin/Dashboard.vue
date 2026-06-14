<template>
  <div class="dashboard">
    <h2 class="page-title">数据概览</h2>
    
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card purple">
          <div class="stat-label">总用户数</div>
          <div class="stat-value">{{ stats.totalUsers }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card green">
          <div class="stat-label">活跃授权</div>
          <div class="stat-value">{{ stats.activeLicenses }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card orange">
          <div class="stat-label">今日订单</div>
          <div class="stat-value">{{ stats.todayOrders }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card blue">
          <div class="stat-label">本月收入</div>
          <div class="stat-value">¥{{ stats.monthlyRevenue }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近活动 -->
    <el-card class="activity-card">
      <template #header>
        <div class="card-header">
          <span>最近活动</span>
        </div>
      </template>
      <el-timeline>
        <el-timeline-item
          v-for="(activity, index) in activities"
          :key="index"
          :timestamp="activity.timestamp"
          :type="activity.type">
          {{ activity.content }}
        </el-timeline-item>
      </el-timeline>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const stats = ref({
  totalUsers: 0,
  activeLicenses: 0,
  todayOrders: 0,
  monthlyRevenue: 0
})

const activities = ref([
  { timestamp: '2026-04-16 18:30', content: '新用户注册：张三', type: 'primary' },
  { timestamp: '2026-04-16 17:45', content: '授权码生成：LIC-2026-001', type: 'success' },
  { timestamp: '2026-04-16 16:20', content: '系统设置更新', type: 'warning' }
])

onMounted(() => {
  // TODO: 调用 API 获取真实数据
  stats.value = {
    totalUsers: 128,
    activeLicenses: 95,
    todayOrders: 23,
    monthlyRevenue: 15800
  }
})
</script>

<style scoped lang="scss">
.dashboard {
  .page-title {
    font-size: 24px;
    margin-bottom: 20px;
    color: #303133;
  }
  
  .stats-row {
    margin-bottom: 20px;
    
    .stat-card {
      color: #fff;
      padding: 20px;
      
      &.purple {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      }
      
      &.green {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
      }
      
      &.orange {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
      }
      
      &.blue {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
      }
      
      .stat-label {
        font-size: 14px;
        opacity: 0.9;
        margin-bottom: 8px;
      }
      
      .stat-value {
        font-size: 28px;
        font-weight: bold;
      }
    }
  }
  
  .activity-card {
    :deep(.el-card__header) {
      padding: 15px 20px;
      border-bottom: 1px solid #ebeef5;
    }
  }
}
</style>

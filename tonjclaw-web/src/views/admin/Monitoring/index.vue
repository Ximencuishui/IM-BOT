<template>
  <div class="monitoring-container">
    <!-- 健康摘要 -->
    <el-card class="health-summary" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>系统健康状态</span>
          <el-tag :type="healthStatus === 'healthy' ? 'success' : 'warning'">
            {{ healthStatus === 'healthy' ? '正常' : '异常' }}
          </el-tag>
        </div>
      </template>
      <el-row :gutter="20">
        <el-col :span="8">
          <div class="metric-item">
            <div class="metric-label">CPU使用率</div>
            <el-progress 
              :percentage="resources.cpu_percent || 0" 
              :color="getProgressColor(resources.cpu_percent)"
            />
          </div>
        </el-col>
        <el-col :span="8">
          <div class="metric-item">
            <div class="metric-label">内存使用率</div>
            <el-progress 
              :percentage="resources.memory_percent || 0"
              :color="getProgressColor(resources.memory_percent)"
            />
          </div>
        </el-col>
        <el-col :span="8">
          <div class="metric-item">
            <div class="metric-label">磁盘使用率</div>
            <el-progress 
              :percentage="resources.disk_percent || 0"
              :color="getProgressColor(resources.disk_percent)"
            />
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 组件状态 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <span>中间件状态</span>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="Redis">
              <el-tag :type="components.redis ? 'success' : 'danger'">
                {{ components.redis ? '已连接' : '未连接' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="RabbitMQ">
              <el-tag :type="components.rabbitmq ? 'success' : 'danger'">
                {{ components.rabbitmq ? '已连接' : '未连接' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="Elasticsearch">
              <el-tag :type="components.elasticsearch ? 'success' : 'danger'">
                {{ components.elasticsearch ? '已连接' : '未连接' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="Database">
              <el-tag :type="components.database ? 'success' : 'danger'">
                {{ components.database ? '已连接' : '未连接' }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <span>应用信息</span>
          </template>
          <el-descriptions :column="1" border v-if="appInfo">
            <el-descriptions-item label="应用名称">{{ appInfo.name }}</el-descriptions-item>
            <el-descriptions-item label="版本">{{ appInfo.version }}</el-descriptions-item>
            <el-descriptions-item label="运行时长">{{ formatUptime(appInfo.uptime) }}</el-descriptions-item>
            <el-descriptions-item label="进程ID">{{ appInfo.pid }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>

    <!-- 系统资源详情 -->
    <el-card style="margin-top: 20px;" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>系统资源详情</span>
          <el-button size="small" @click="refreshData">
            <el-icon><Refresh /></el-icon> 刷新
          </el-button>
        </div>
      </template>
      <el-tabs v-model="activeTab">
        <el-tab-pane label="CPU" name="cpu">
          <el-descriptions :column="2" border v-if="systemStatus">
            <el-descriptions-item label="使用率">{{ systemStatus.cpu.percent }}%</el-descriptions-item>
            <el-descriptions-item label="核心数">{{ systemStatus.cpu.count }}</el-descriptions-item>
            <el-descriptions-item label="频率">{{ (systemStatus.cpu.frequency / 1000).toFixed(2) }} GHz</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>
        <el-tab-pane label="内存" name="memory">
          <el-descriptions :column="2" border v-if="systemStatus">
            <el-descriptions-item label="总计">{{ formatBytes(systemStatus.memory.total) }}</el-descriptions-item>
            <el-descriptions-item label="已用">{{ formatBytes(systemStatus.memory.used) }}</el-descriptions-item>
            <el-descriptions-item label="可用">{{ formatBytes(systemStatus.memory.available) }}</el-descriptions-item>
            <el-descriptions-item label="使用率">{{ systemStatus.memory.percent }}%</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>
        <el-tab-pane label="磁盘" name="disk">
          <el-descriptions :column="2" border v-if="systemStatus">
            <el-descriptions-item label="总计">{{ formatBytes(systemStatus.disk.total) }}</el-descriptions-item>
            <el-descriptions-item label="已用">{{ formatBytes(systemStatus.disk.used) }}</el-descriptions-item>
            <el-descriptions-item label="可用">{{ formatBytes(systemStatus.disk.free) }}</el-descriptions-item>
            <el-descriptions-item label="使用率">{{ systemStatus.disk.percent }}%</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>
        <el-tab-pane label="网络" name="network">
          <el-descriptions :column="2" border v-if="systemStatus">
            <el-descriptions-item label="发送字节">{{ formatBytes(systemStatus.network.bytes_sent) }}</el-descriptions-item>
            <el-descriptions-item label="接收字节">{{ formatBytes(systemStatus.network.bytes_recv) }}</el-descriptions-item>
            <el-descriptions-item label="发送包数">{{ systemStatus.network.packets_sent }}</el-descriptions-item>
            <el-descriptions-item label="接收包数">{{ systemStatus.network.packets_recv }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 最近活动 -->
    <el-card style="margin-top: 20px;" shadow="hover">
      <template #header>
        <span>最近活动</span>
      </template>
      <el-timeline>
        <el-timeline-item
          v-for="activity in activities"
          :key="activity.id"
          :timestamp="formatDateTime(activity.created_at)"
          :type="activity.status === 'success' ? 'success' : 'danger'"
        >
          <div class="activity-item">
            <strong>{{ activity.username || '未知用户' }}</strong>
            <span class="activity-action">{{ getActivityLabel(activity.action) }}</span>
            <span class="activity-desc">{{ activity.description }}</span>
          </div>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-if="activities.length === 0" description="暂无活动记录" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import {
  getSystemStatus,
  getAppStatus,
  getHealthSummary,
  getRecentActivities
} from '@/api/admin/monitoring'

const activeTab = ref('cpu')
const healthStatus = ref('healthy')
const resources = reactive({
  cpu_percent: 0,
  memory_percent: 0,
  disk_percent: 0
})
const components = reactive({
  redis: false,
  rabbitmq: false,
  elasticsearch: false,
  database: false
})
const appInfo = ref(null)
const systemStatus = ref(null)
const activities = ref([])

let refreshTimer = null

// 加载数据
const loadAllData = async () => {
  await Promise.all([
    loadHealthSummary(),
    loadAppStatus(),
    loadSystemStatus(),
    loadActivities()
  ])
}

const loadHealthSummary = async () => {
  try {
    const res = await getHealthSummary()
    if (res.success) {
      healthStatus.value = res.overall_status
      Object.assign(resources, res.resources)
      Object.assign(components, res.components)
    }
  } catch (error) {
    console.error('加载健康摘要失败:', error)
  }
}

const loadAppStatus = async () => {
  try {
    const res = await getAppStatus()
    if (res.success) {
      appInfo.value = res.app
    }
  } catch (error) {
    console.error('加载应用状态失败:', error)
  }
}

const loadSystemStatus = async () => {
  try {
    const res = await getSystemStatus()
    if (res.success) {
      systemStatus.value = res.system
    }
  } catch (error) {
    console.error('加载系统状态失败:', error)
  }
}

const loadActivities = async () => {
  try {
    const res = await getRecentActivities()
    if (res.success) {
      activities.value = res.activities
    }
  } catch (error) {
    console.error('加载活动记录失败:', error)
  }
}

const refreshData = () => {
  loadAllData()
  ElMessage.success('数据已刷新')
}

// 格式化字节
const formatBytes = (bytes) => {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i]
}

// 格式化运行时间
const formatUptime = (seconds) => {
  if (!seconds) return '-'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return `${hours}小时${minutes}分钟`
}

// 格式化日期时间
const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

// 获取进度条颜色
const getProgressColor = (percent) => {
  if (percent < 60) return '#67c23a'
  if (percent < 80) return '#e6a23c'
  return '#f56c6c'
}

// 获取操作标签
const getActivityLabel = (action) => {
  const labels = {
    login: '登录',
    logout: '登出',
    create: '创建',
    update: '更新',
    delete: '删除',
    export: '导出'
  }
  return labels[action] || action
}

onMounted(() => {
  loadAllData()
  // 每30秒自动刷新
  refreshTimer = setInterval(loadAllData, 30000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.monitoring-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.metric-item {
  text-align: center;
}

.metric-label {
  margin-bottom: 10px;
  font-size: 14px;
  color: #606266;
}

.activity-item {
  line-height: 1.8;
}

.activity-action {
  margin: 0 8px;
  color: #409eff;
}

.activity-desc {
  color: #909399;
}
</style>
﻿﻿﻿<template>
  <div class="audit-logs-page">
    <div class="page-header">
      <h2 class="page-title">审计日志</h2>
      <el-button type="primary" @click="handleExport">
        <el-icon><Download /></el-icon> 导出日志
      </el-button>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon blue">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-info">
              <p class="stat-value">{{ stats.total_logs }}</p>
              <p class="stat-label">日志总数</p>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon green">
              <el-icon><Clock /></el-icon>
            </div>
            <div class="stat-info">
              <p class="stat-value">{{ stats.today_logs }}</p>
              <p class="stat-label">今日日志</p>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon orange">
              <el-icon><User /></el-icon>
            </div>
            <div class="stat-info">
              <p class="stat-value">{{ actionTypeCount }}</p>
              <p class="stat-label">操作类型</p>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon purple">
              <el-icon><Delete /></el-icon>
            </div>
            <div class="stat-info">
              <p class="stat-value">90天</p>
              <p class="stat-label">自动清理</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 搜索�?-->
    <el-card class="search-card">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="操作类型">
          <el-select v-model="searchForm.action_type" placeholder="选择操作类型" clearable>
            <el-option v-for="type in actionTypes" :key="type.value" :label="type.label" :value="type.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="用户ID">
          <el-input v-model="searchForm.user_id" placeholder="用户ID" clearable type="number" />
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="searchForm.start_date" type="date" placeholder="开始日期" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="searchForm.end_date" type="date" placeholder="结束日期" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 操作类型统计图表 -->
    <el-card class="chart-card" v-if="actionStats">
      <template #header>
        <span>操作类型统计</span>
      </template>
      <div ref="actionChart" class="chart-container"></div>
    </el-card>

    <!-- 日志列表 -->
    <el-card class="table-card">
      <el-table :data="logs" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="操作用户" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ row.username || `用户${row.user_id}` }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="action_type" label="操作类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getActionTypeTag(row.action_type)">
              {{ getActionTypeLabel(row.action_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="操作描述" />
        <el-table-column prop="ip_address" label="IP地址" width="130">
          <template #default="{ row }">
            <span>{{ row.ip_address || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="操作时间" width="160" />
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
        style="margin-top: 20px; justify-content: flex-end"
      />
    </el-card>

    <!-- 清理日志对话�?-->
    <el-dialog
      v-model="showCleanupDialog"
      title="清理旧日志"
      width="400px"
    >
      <el-alert
        title="注意：此操作将删除指定天数之前的所有日志，无法恢复"
        type="warning"
        :closable="false"
        style="margin-bottom: 20px"
      />
      <el-form :model="cleanupForm" label-width="100px">
        <el-form-item label="保留天数">
          <el-input-number v-model="cleanupForm.days" :min="7" :max="365" />
          <span style="margin-left: 10px">天</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCleanupDialog = false">取消</el-button>
        <el-button type="danger" @click="handleCleanup" :loading="cleaning">
          确认清理
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Document, Clock, User, Delete } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getAuditLogs, getAuditStats, exportAuditLogs, cleanupOldLogs } from '../../../api/admin/auditLogs'

const loading = ref(false)
const cleaning = ref(false)
const showCleanupDialog = ref(false)

const logs = ref([])
const stats = reactive({
  total_logs: 0,
  today_logs: 0,
  action_stats: {}
})

const actionStats = ref(null)

const searchForm = reactive({
  action_type: '',
  user_id: '',
  start_date: '',
  end_date: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const cleanupForm = reactive({
  days: 90
})

const actionTypes = [
  { label: '用户登录', value: 'user_login' },
  { label: '用户登出', value: 'user_logout' },
  { label: '用户创建', value: 'user_create' },
  { label: '用户更新', value: 'user_update' },
  { label: '用户删除', value: 'user_delete' },
  { label: '密码重置', value: 'password_reset' },
  { label: '权限更新', value: 'permission_update' },
  { label: '授权码生成', value: 'license_generate' },
  { label: '授权码撤销', value: 'license_revoke' },
  { label: '订单创建', value: 'order_create' },
  { label: '订单更新', value: 'order_update' },
  { label: '系统设置', value: 'system_setting' },
  { label: '数据导出', value: 'data_export' },
  { label: '日志清理', value: 'log_cleanup' }
]

const actionTypeCount = computed(() => Object.keys(stats.action_stats).length)

let actionChart = null
const actionChartRef = ref(null)

const loadLogs = async () => {
  loading.value = true
  try {
    const params = {
      ...searchForm,
      page: pagination.page,
      per_page: pagination.pageSize
    }
    
    const res = await getAuditLogs(params)
    if (res.success) {
      logs.value = res.logs || []
      pagination.total = res.pagination?.total || 0
    }
  } catch (error) {
    console.error('加载审计日志失败:', error)
    ElMessage.error('加载审计日志失败')
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  try {
    const res = await getAuditStats()
    if (res.success) {
      Object.assign(stats, res)
      actionStats.value = res.action_stats
      updateActionChart()
    }
  } catch (error) {
    console.error('加载统计信息失败:', error)
  }
}

const updateActionChart = () => {
  if (!actionChart || !actionStats.value) return
  
  const labels = []
  const values = []
  
  Object.entries(actionStats.value).forEach(([type, count]) => {
    labels.push(getActionTypeLabel(type))
    values.push(count)
  })
  
  actionChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: labels,
      axisLabel: { rotate: 45 }
    },
    yAxis: {
      type: 'value',
      name: '次数'
    },
    series: [{
      type: 'bar',
      data: values,
      itemStyle: {
        borderRadius: [4, 4, 0, 0],
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#409EFF' },
          { offset: 1, color: '#79bbff' }
        ])
      }
    }]
  })
}

const handleSearch = () => {
  pagination.page = 1
  loadLogs()
}

const handleReset = () => {
  Object.assign(searchForm, {
    action_type: '',
    user_id: '',
    start_date: '',
    end_date: ''
  })
  handleSearch()
}

const handlePageChange = (page) => {
  pagination.page = page
  loadLogs()
}

const handleSizeChange = (size) => {
  pagination.pageSize = size
  pagination.page = 1
  loadLogs()
}

const handleExport = async () => {
  try {
    const data = {
      start_date: searchForm.start_date,
      end_date: searchForm.end_date
    }
    
    const res = await exportAuditLogs(data)
    const blob = new Blob([res], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'audit_logs.csv'
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success('日志导出成功')
  } catch (error) {
    console.error('导出日志失败:', error)
    ElMessage.error('导出日志失败')
  }
}

const handleCleanup = async () => {
  ElMessageBox.confirm(
    `确定要清�?${cleanupForm.days} 天之前的所有日志吗？此操作无法恢复！`,
    '警告',
    {
      confirmButtonText: '确定清理',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    cleaning.value = true
    try {
      const res = await cleanupOldLogs(cleanupForm.days)
      if (res.success) {
        ElMessage.success(res.message)
        showCleanupDialog.value = false
        await loadLogs()
        await loadStats()
      } else {
        ElMessage.error(res.message || '清理失败')
      }
    } catch (error) {
      console.error('清理日志失败:', error)
      ElMessage.error('清理日志失败')
    } finally {
      cleaning.value = false
    }
  }).catch(() => {})
}

const getActionTypeLabel = (type) => {
  const map = {
    user_login: '用户登录',
    user_logout: '用户登出',
    user_create: '用户创建',
    user_update: '用户更新',
    user_delete: '用户删除',
    password_reset: '密码重置',
    permission_update: '权限更新',
    license_generate: '授权码生成',
    license_revoke: '授权码撤销',
    order_create: '订单创建',
    order_update: '订单更新',
    system_setting: '系统设置',
    data_export: '数据导出',
    log_cleanup: '日志清理'
  }
  return map[type] || type
}

const getActionTypeTag = (type) => {
  const map = {
    user_login: 'success',
    user_logout: 'info',
    user_create: 'primary',
    user_update: 'warning',
    user_delete: 'danger',
    password_reset: 'danger',
    permission_update: 'warning',
    license_generate: 'primary',
    license_revoke: 'danger',
    order_create: 'success',
    order_update: 'warning',
    system_setting: 'info',
    data_export: 'primary',
    log_cleanup: 'danger'
  }
  return map[type] || 'info'
}

const initChart = () => {
  if (actionChartRef.value) {
    actionChart = echarts.init(actionChartRef.value)
  }
}

const resizeChart = () => {
  actionChart?.resize()
}

watch(actionStats, () => {
  updateActionChart()
})

onMounted(() => {
  initChart()
  loadLogs()
  loadStats()
  window.addEventListener('resize', resizeChart)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeChart)
  actionChart?.dispose()
})
</script>

<style scoped lang="scss">
.audit-logs-page {
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    
    .page-title {
      font-size: 24px;
      color: #303133;
      margin: 0;
    }
  }
  
  .stats-row {
    margin-bottom: 20px;
  }
  
  .stat-card {
    ::deep(.el-card__body) {
      padding: 0;
    }
    
    .stat-content {
      display: flex;
      align-items: center;
      padding: 20px;
      gap: 15px;
    }
    
    .stat-icon {
      width: 56px;
      height: 56px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 28px;
      
      &.blue { background: linear-gradient(135deg, #e8f4fd 0%, #d4ebfa 100%); color: #409EFF; }
      &.green { background: linear-gradient(135deg, #f0f9eb 0%, #e1f3d8 100%); color: #67C23A; }
      &.orange { background: linear-gradient(135deg, #fff7e6 0%, #ffeeba 100%); color: #E6A23C; }
      &.purple { background: linear-gradient(135deg, #f3e8ff 0%, #e9d5ff 100%); color: #9B59B6; }
    }
    
    .stat-info {
      flex: 1;
      
      .stat-value {
        font-size: 24px;
        font-weight: bold;
        color: #303133;
        margin: 0;
      }
      
      .stat-label {
        font-size: 14px;
        color: #909399;
        margin: 4px 0;
      }
    }
  }
  
  .search-card {
    margin-bottom: 20px;
  }
  
  .chart-card {
    margin-bottom: 20px;
    
    ::deep(.el-card__body) {
      padding: 20px;
    }
    
    .chart-container {
      height: 250px;
    }
  }
  
  .table-card {
    ::deep(.el-card__body) {
      padding: 20px;
    }
  }
}
</style>
<template>
  <div class="audit-logs-container">
    <!-- 统计卡片 -->
    <el-row :gutter="20" style="margin-bottom: 20px;">
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="总日志数" :value="stats.total_logs || 0" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="今日日志" :value="stats.today_logs || 0" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="成功操作" :value="successCount" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="失败操作" :value="failedCount" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 日志列表 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>审计日志</span>
          <div class="header-actions">
            <el-button size="small" @click="showCleanupDialog = true">
              <el-icon><Delete /></el-icon> 清理日志
            </el-button>
            <el-button size="small" type="primary" @click="exportLogs">
              <el-icon><Download /></el-icon> 导出
            </el-button>
          </div>
        </div>
      </template>

      <!-- 搜索过滤 -->
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="用户">
          <el-input v-model="searchForm.keyword" placeholder="用户名/IP" clearable style="width: 150px" />
        </el-form-item>
        <el-form-item label="操作类型">
          <el-select v-model="searchForm.action" placeholder="全部" clearable style="width: 120px">
            <el-option label="登录" value="login" />
            <el-option label="登出" value="logout" />
            <el-option label="创建" value="create" />
            <el-option label="更新" value="update" />
            <el-option label="删除" value="delete" />
            <el-option label="导出" value="export" />
          </el-select>
        </el-form-item>
        <el-form-item label="资源类型">
          <el-select v-model="searchForm.resource" placeholder="全部" clearable style="width: 120px">
            <el-option label="用户" value="user" />
            <el-option label="授权码" value="license" />
            <el-option label="订单" value="order" />
            <el-option label="商品" value="product" />
            <el-option label="配置" value="config" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="全部" clearable style="width: 100px">
            <el-option label="成功" value="success" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            style="width: 240px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadLogs">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 表格 -->
      <el-table :data="logs" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="用户" width="120" show-overflow-tooltip />
        <el-table-column label="操作类型" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ getActionLabel(row.action) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="资源" width="100">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ getResourceLabel(row.resource) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="ip_address" label="IP地址" width="130" />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
              {{ row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="170">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="viewDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadLogs"
        @current-change="loadLogs"
        style="margin-top: 20px; justify-content: flex-end"
      />
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="showDetailDialog" title="日志详情" width="700px">
      <el-descriptions :column="1" border v-if="currentLog">
        <el-descriptions-item label="ID">{{ currentLog.id }}</el-descriptions-item>
        <el-descriptions-item label="用户">{{ currentLog.username || '-' }}</el-descriptions-item>
        <el-descriptions-item label="操作类型">{{ getActionLabel(currentLog.action) }}</el-descriptions-item>
        <el-descriptions-item label="资源">{{ getResourceLabel(currentLog.resource) }}</el-descriptions-item>
        <el-descriptions-item label="资源ID">{{ currentLog.resource_id || '-' }}</el-descriptions-item>
        <el-descriptions-item label="描述">{{ currentLog.description }}</el-descriptions-item>
        <el-descriptions-item label="IP地址">{{ currentLog.ip_address || '-' }}</el-descriptions-item>
        <el-descriptions-item label="User Agent">{{ currentLog.user_agent || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="currentLog.status === 'success' ? 'success' : 'danger'">
            {{ currentLog.status === 'success' ? '成功' : '失败' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="错误信息" v-if="currentLog.error_message">
          {{ currentLog.error_message }}
        </el-descriptions-item>
        <el-descriptions-item label="旧值" v-if="currentLog.old_value">
          <pre>{{ JSON.stringify(currentLog.old_value, null, 2) }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="新值" v-if="currentLog.new_value">
          <pre>{{ JSON.stringify(currentLog.new_value, null, 2) }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="时间">{{ formatDateTime(currentLog.created_at) }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="showDetailDialog = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 清理日志对话框 -->
    <el-dialog v-model="showCleanupDialog" title="清理日志" width="500px">
      <el-alert
        title="警告：此操作将永久删除指定天数前的日志，不可恢复！"
        type="warning"
        :closable="false"
        style="margin-bottom: 20px"
      />
      <el-form :model="cleanupForm" label-width="120px">
        <el-form-item label="保留天数" required>
          <el-input-number 
            v-model="cleanupForm.days" 
            :min="1" 
            :max="365"
            controls-position="right"
          />
          <span class="form-tip">天（将删除此天数之前的所有日志）</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCleanupDialog = false">取消</el-button>
        <el-button type="danger" @click="confirmCleanup" :loading="cleaning">确认清理</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Download } from '@element-plus/icons-vue'
import {
  getAuditLogs,
  getAuditStats,
  exportAuditLogs,
  cleanupOldLogs
} from '@/api/admin/auditLogs'
import dayjs from 'dayjs'

// 数据
const logs = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 统计
const stats = reactive({
  total_logs: 0,
  today_logs: 0
})

// 搜索表单
const searchForm = reactive({
  keyword: '',
  action: '',
  resource: '',
  status: ''
})
const dateRange = ref([])

// 对话框
const showDetailDialog = ref(false)
const showCleanupDialog = ref(false)
const currentLog = ref(null)
const cleaning = ref(false)
const cleanupForm = reactive({
  days: 90
})

// 计算属性
const successCount = computed(() => {
  const stat = stats.status_stats?.find(s => s.status === 'success')
  return stat?.count || 0
})

const failedCount = computed(() => {
  const stat = stats.status_stats?.find(s => s.status === 'failed')
  return stat?.count || 0
})

// 加载数据
const loadAllData = async () => {
  await Promise.all([
    loadLogs(),
    loadStats()
  ])
}

const loadLogs = async () => {
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      per_page: pageSize.value,
      ...searchForm
    }
    
    if (dateRange.value && dateRange.value.length === 2) {
      params.start_date = dayjs(dateRange.value[0]).format('YYYY-MM-DD')
      params.end_date = dayjs(dateRange.value[1]).format('YYYY-MM-DD')
    }
    
    const res = await getAuditLogs(params)
    if (res.success) {
      logs.value = res.logs || []
      total.value = res.total || 0
    } else {
      ElMessage.error(res.message || '加载失败')
    }
  } catch (error) {
    ElMessage.error('加载失败：' + error.message)
  } finally {
    loading.value = false
  }
}

const loadStats = async () => {
  try {
    const res = await getAuditStats()
    if (res.success) {
      Object.assign(stats, res.stats)
    }
  } catch (error) {
    console.error('加载统计失败:', error)
  }
}

// 查看详情
const viewDetail = (log) => {
  currentLog.value = log
  showDetailDialog.value = true
}

// 导出日志
const exportLogs = async () => {
  try {
    const data = {
      start_date: dateRange.value && dateRange.value.length === 2 
        ? dayjs(dateRange.value[0]).format('YYYY-MM-DD') 
        : undefined,
      end_date: dateRange.value && dateRange.value.length === 2 
        ? dayjs(dateRange.value[1]).format('YYYY-MM-DD') 
        : undefined,
      action: searchForm.action || undefined,
      resource: searchForm.resource || undefined
    }
    
    const res = await exportAuditLogs(data)
    if (res.success) {
      // 下载CSV文件
      const blob = new Blob([res.csv_data], { type: 'text/csv;charset=utf-8;' })
      const link = document.createElement('a')
      const url = URL.createObjectURL(blob)
      link.setAttribute('href', url)
      link.setAttribute('download', `audit_logs_${dayjs().format('YYYYMMDD_HHmmss')}.csv`)
      link.style.visibility = 'hidden'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      ElMessage.success(`已导出 ${res.count} 条记录`)
    } else {
      ElMessage.error(res.message || '导出失败')
    }
  } catch (error) {
    ElMessage.error('导出失败：' + error.message)
  }
}

// 清理日志
const confirmCleanup = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要清理 ${cleanupForm.days} 天前的所有日志吗？此操作不可恢复！`,
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    cleaning.value = true
    const res = await cleanupOldLogs(cleanupForm.days)
    if (res.success) {
      ElMessage.success(res.message)
      showCleanupDialog.value = false
      await loadAllData()
    } else {
      ElMessage.error(res.message || '清理失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('清理失败：' + error.message)
    }
  } finally {
    cleaning.value = false
  }
}

// 重置搜索
const resetSearch = () => {
  Object.assign(searchForm, {
    keyword: '',
    action: '',
    resource: '',
    status: ''
  })
  dateRange.value = []
  currentPage.value = 1
  loadLogs()
}

// 格式化日期时间
const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  return dayjs(dateStr).format('YYYY-MM-DD HH:mm:ss')
}

// 获取操作标签
const getActionLabel = (action) => {
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

// 获取资源标签
const getResourceLabel = (resource) => {
  const labels = {
    user: '用户',
    license: '授权码',
    order: '订单',
    product: '商品',
    config: '配置'
  }
  return labels[resource] || resource || '-'
}

onMounted(() => {
  loadAllData()
})
</script>

<style scoped>
.audit-logs-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.search-form {
  margin-bottom: 20px;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-left: 10px;
}

pre {
  background-color: #f5f7fa;
  padding: 10px;
  border-radius: 4px;
  max-height: 200px;
  overflow-y: auto;
}
</style>
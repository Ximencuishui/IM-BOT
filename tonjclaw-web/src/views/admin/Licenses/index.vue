<template>
  <div class="licenses-container">
    <!-- 页面标题和操作按钮 -->
    <div class="page-header">
      <h2>授权码管理</h2>
      <div class="header-actions">
        <el-button type="primary" @click="showGenerateDialog = true">
          <el-icon><Plus /></el-icon> 生成授权码
        </el-button>
        <el-button 
          type="success" 
          @click="handleBatchExtend" 
          :disabled="selectedLicenses.length === 0"
        >
          批量展期 ({{ selectedLicenses.length }})
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-cards">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-label">总授权数</div>
            <div class="stat-value">{{ stats.total }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-label">有效授权</div>
            <div class="stat-value">{{ stats.active }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-label">即将到期</div>
            <div class="stat-value">{{ stats.expiring }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-label">已撤销</div>
            <div class="stat-value">{{ stats.revoked }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 搜索和筛选 -->
    <el-card class="filter-card">
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="授权码">
          <el-input v-model="searchForm.license_code" placeholder="请输入授权码" clearable />
        </el-form-item>
        <el-form-item label="用户邮箱">
          <el-input v-model="searchForm.user_email" placeholder="请输入用户邮箱" clearable />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="请选择状态" clearable>
            <el-option label="全部" value="" />
            <el-option label="有效" value="active" />
            <el-option label="无效" value="inactive" />
            <el-option label="已撤销" value="revoked" />
          </el-select>
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="searchForm.type" placeholder="请选择类型" clearable>
            <el-option label="全部" value="" />
            <el-option label="月付" value="monthly" />
            <el-option label="年付" value="yearly" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 授权码表格 -->
    <el-card class="table-card">
      <el-table 
        :data="licenses" 
        style="width: 100%" 
        v-loading="loading"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="license_code" label="授权码" width="200" />
        <el-table-column prop="user_email" label="用户邮箱" width="180" />
        <el-table-column prop="bound_to" label="绑定群ID" width="150" />
        <el-table-column prop="license_type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.license_type === 'yearly' ? 'success' : 'info'">
              {{ row.license_type === 'yearly' ? '年付' : '月付' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="expires_at" label="到期时间" width="150">
          <template #default="{ row }">
            {{ formatDate(row.expires_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="days_remaining" label="剩余天数" width="100">
          <template #default="{ row }">
            <span :class="getDaysRemainingClass(row.days_remaining)">
              {{ row.days_remaining }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row)">
              {{ getStatusText(row) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="viewLicenseDetail(row)">详情</el-button>
            <el-button size="small" type="primary" @click="showExtendDialog(row)">展期</el-button>
            <el-button size="small" type="danger" @click="confirmRevoke(row)">撤销</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 生成授权码对话框 -->
    <el-dialog v-model="showGenerateDialog" title="生成授权码" width="500px">
      <el-form :model="generateForm" label-width="100px">
        <el-form-item label="授权类型">
          <el-radio-group v-model="generateForm.license_type">
            <el-radio label="monthly">月付</el-radio>
            <el-radio label="yearly">年付</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="绑定群ID">
          <el-input v-model="generateForm.bound_to" placeholder="可选，留空则不绑定" />
        </el-form-item>
        <el-form-item label="生成数量">
          <el-input-number v-model="generateForm.count" :min="1" :max="100" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showGenerateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleGenerateLicense" :loading="generating">
          生成
        </el-button>
      </template>
    </el-dialog>

    <!-- 展期对话框 -->
    <el-dialog v-model="showExtendDialogVisible" title="授权码展期" width="400px">
      <el-form :model="extendForm" label-width="100px">
        <el-form-item label="授权码">
          <el-input v-model="extendForm.license_code" disabled />
        </el-form-item>
        <el-form-item label="当前到期">
          <el-input :value="formatDate(extendForm.current_expiry)" disabled />
        </el-form-item>
        <el-form-item label="展期月数">
          <el-select v-model="extendForm.months" placeholder="请选择展期月数">
            <el-option label="1个月" :value="1" />
            <el-option label="3个月" :value="3" />
            <el-option label="6个月" :value="6" />
            <el-option label="12个月" :value="12" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showExtendDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleExtendLicense" :loading="extending">
          确认展期
        </el-button>
      </template>
    </el-dialog>

    <!-- 批量展期对话框 -->
    <el-dialog v-model="showBatchExtendDialog" title="批量展期" width="500px">
      <div class="batch-extend-content">
        <p>已选择 <strong>{{ selectedLicenses.length }}</strong> 个授权码进行展期</p>
        <el-table :data="selectedLicenses.slice(0, 5)" style="width: 100%; margin: 10px 0;">
          <el-table-column prop="license_code" label="授权码" />
          <el-table-column prop="bound_to" label="绑定群" />
        </el-table>
        <p v-if="selectedLicenses.length > 5" style="color: #909399; font-size: 12px;">
          ... 还有 {{ selectedLicenses.length - 5 }} 个授权码
        </p>
        
        <el-form :model="batchExtendForm" label-width="100px" style="margin-top: 20px;">
          <el-form-item label="展期月数">
            <el-select v-model="batchExtendForm.months" placeholder="请选择展期月数">
              <el-option label="1个月" :value="1" />
              <el-option label="3个月" :value="3" />
              <el-option label="6个月" :value="6" />
              <el-option label="12个月" :value="12" />
            </el-select>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="showBatchExtendDialog = false">取消</el-button>
        <el-button type="primary" @click="handleBatchExtendConfirm" :loading="batchExtending">
          确认展期
        </el-button>
      </template>
    </el-dialog>

    <!-- 授权码详情对话框 -->
    <el-dialog v-model="showDetailDialog" title="授权码详情" width="600px">
      <div v-if="currentLicense" class="license-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="授权码">{{ currentLicense.license_code }}</el-descriptions-item>
          <el-descriptions-item label="授权类型">
            <el-tag :type="currentLicense.license_type === 'yearly' ? 'success' : 'info'">
              {{ currentLicense.license_type === 'yearly' ? '年付' : '月付' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="用户邮箱">{{ currentLicense.user_email || '-' }}</el-descriptions-item>
          <el-descriptions-item label="绑定群ID">{{ currentLicense.bound_to || '-' }}</el-descriptions-item>
          <el-descriptions-item label="激活时间">{{ formatDate(currentLicense.activated_at) }}</el-descriptions-item>
          <el-descriptions-item label="到期时间">{{ formatDate(currentLicense.expires_at) }}</el-descriptions-item>
          <el-descriptions-item label="剩余天数">{{ currentLicense.days_remaining }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(currentLicense)">
              {{ getStatusText(currentLicense) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="机器指纹">{{ currentLicense.machine_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDate(currentLicense.created_at) }}</el-descriptions-item>
        </el-descriptions>
      </div>
      <template #footer>
        <el-button @click="showDetailDialog = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { 
  getLicenses, 
  generateLicense, 
  revokeLicense, 
  extendLicense, 
  batchExtendLicenses,
  getLicenseStats 
} from '@/api/admin/licenses'

// 数据
const licenses = ref([])
const loading = ref(false)
const generating = ref(false)
const extending = ref(false)
const batchExtending = ref(false)
const selectedLicenses = ref([])

// 统计信息
const stats = reactive({
  total: 0,
  active: 0,
  expiring: 0,
  revoked: 0
})

// 搜索表单
const searchForm = reactive({
  license_code: '',
  user_email: '',
  status: '',
  type: ''
})

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 生成授权码表单
const showGenerateDialog = ref(false)
const generateForm = reactive({
  license_type: 'monthly',
  bound_to: '',
  count: 1
})

// 展期表单
const showExtendDialogVisible = ref(false)
const extendForm = reactive({
  id: null,
  license_code: '',
  current_expiry: '',
  months: 1
})

// 批量展期
const showBatchExtendDialog = ref(false)
const batchExtendForm = reactive({
  months: 1
})

// 详情对话框
const showDetailDialog = ref(false)
const currentLicense = ref(null)

// 加载授权码列表
const loadLicenses = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      per_page: pagination.pageSize,
      ...searchForm
    }
    
    const response = await getLicenses(params)
    if (response.success) {
      licenses.value = response.licenses || []
      pagination.total = response.pagination?.total || licenses.value.length
    }
  } catch (error) {
    ElMessage.error('加载授权码列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// 加载统计信息
const loadStats = async () => {
  try {
    const response = await getLicenseStats()
    if (response.success) {
      Object.assign(stats, response.stats)
    }
  } catch (error) {
    console.error('加载统计信息失败', error)
  }
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  loadLicenses()
}

// 重置搜索
const resetSearch = () => {
  Object.assign(searchForm, {
    license_code: '',
    user_email: '',
    status: '',
    type: ''
  })
  pagination.page = 1
  loadLicenses()
}

// 分页变化
const handlePageChange = (page) => {
  pagination.page = page
  loadLicenses()
}

const handleSizeChange = (size) => {
  pagination.pageSize = size
  pagination.page = 1
  loadLicenses()
}

// 选择变化
const handleSelectionChange = (selection) => {
  selectedLicenses.value = selection
}

// 生成授权码
const handleGenerateLicense = async () => {
  generating.value = true
  try {
    // 如果生成多个，需要循环调用
    const results = []
    for (let i = 0; i < generateForm.count; i++) {
      const response = await generateLicense({
        license_type: generateForm.license_type,
        bound_to: generateForm.bound_to || undefined
      })
      if (response.success) {
        results.push(response.license)
      }
    }
    
    if (results.length > 0) {
      ElMessage.success(`成功生成 ${results.length} 个授权码`)
      showGenerateDialog.value = false
      loadLicenses()
      loadStats()
      
      // 显示生成的授权码
      if (results.length <= 5) {
        const codes = results.map(r => r.license_code).join('\n')
        ElMessageBox.alert(codes, '生成的授权码', {
          confirmButtonText: '确定'
        })
      }
    } else {
      ElMessage.error('生成授权码失败')
    }
  } catch (error) {
    ElMessage.error('生成授权码失败')
    console.error(error)
  } finally {
    generating.value = false
  }
}

// 查看授权码详情
const viewLicenseDetail = (license) => {
  currentLicense.value = license
  showDetailDialog.value = true
}

// 显示展期对话框
const showExtendDialog = (license) => {
  extendForm.id = license.id
  extendForm.license_code = license.license_code
  extendForm.current_expiry = license.expires_at
  extendForm.months = 1
  showExtendDialogVisible.value = true
}

// 执行展期
const handleExtendLicense = async () => {
  extending.value = true
  try {
    const response = await extendLicense(extendForm.id, {
      months: extendForm.months
    })
    
    if (response.success) {
      ElMessage.success(response.message || '展期成功')
      showExtendDialogVisible.value = false
      loadLicenses()
      loadStats()
    } else {
      ElMessage.error(response.error || '展期失败')
    }
  } catch (error) {
    ElMessage.error('展期失败')
    console.error(error)
  } finally {
    extending.value = false
  }
}

// 确认撤销
const confirmRevoke = async (license) => {
  try {
    await ElMessageBox.confirm(
      `确定要撤销授权码 ${license.license_code} 吗？此操作不可恢复！`,
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const response = await revokeLicense(license.id)
    if (response.success) {
      ElMessage.success('授权码已撤销')
      loadLicenses()
      loadStats()
    } else {
      ElMessage.error(response.error || '撤销失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('撤销失败')
      console.error(error)
    }
  }
}

// 显示批量展期对话框
const handleBatchExtend = () => {
  if (selectedLicenses.value.length === 0) {
    ElMessage.warning('请先选择要展期的授权码')
    return
  }
  batchExtendForm.months = 1
  showBatchExtendDialog.value = true
}

// 执行批量展期
const handleBatchExtendConfirm = async () => {
  batchExtending.value = true
  try {
    const licenseIds = selectedLicenses.value.map(l => l.id)
    const response = await batchExtendLicenses({
      license_ids: licenseIds,
      months: batchExtendForm.months
    })
    
    if (response.success) {
      ElMessage.success(response.message || '批量展期成功')
      showBatchExtendDialog.value = false
      selectedLicenses.value = []
      loadLicenses()
      loadStats()
    } else {
      ElMessage.error(response.error || '批量展期失败')
    }
  } catch (error) {
    ElMessage.error('批量展期失败')
    console.error(error)
  } finally {
    batchExtending.value = false
  }
}

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('zh-CN')
}

// 获取状态类型
const getStatusType = (license) => {
  if (license.is_revoked) return 'danger'
  if (!license.is_active) return 'info'
  
  const days = license.days_remaining
  if (days <= 0) return 'danger'
  if (days <= 7) return 'warning'
  return 'success'
}

// 获取状态文本
const getStatusText = (license) => {
  if (license.is_revoked) return '已撤销'
  if (!license.is_active) return '未激活'
  
  const days = license.days_remaining
  if (days <= 0) return '已过期'
  if (days <= 7) return '即将到期'
  return '有效'
}

// 获取剩余天数样式类
const getDaysRemainingClass = (days) => {
  if (days <= 0) return 'text-danger'
  if (days <= 7) return 'text-warning'
  return 'text-success'
}

// 初始化
onMounted(() => {
  loadLicenses()
  loadStats()
})
</script>

<style scoped>
.licenses-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.stats-cards {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
}

.stat-content {
  padding: 10px 0;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.filter-card {
  margin-bottom: 20px;
}

.search-form {
  margin-bottom: 0;
}

.table-card {
  margin-bottom: 20px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.batch-extend-content p {
  margin: 10px 0;
}

.text-success {
  color: #67c23a;
}

.text-warning {
  color: #e6a23c;
}

.text-danger {
  color: #f56c6c;
}

.license-detail {
  padding: 10px 0;
}
</style>
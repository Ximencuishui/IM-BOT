<template>
  <div class="licenses-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>授权码管理</h2>
      <el-button type="primary" @click="showActivateDialog = true">
        <el-icon><Plus /></el-icon> 激活授权码
      </el-button>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-cards">
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card purple">
          <div class="stat-label">总授权数</div>
          <div class="stat-value">{{ stats.total }}</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card green">
          <div class="stat-label">有效授权</div>
          <div class="stat-value">{{ stats.active }}</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card orange">
          <div class="stat-label">即将到期</div>
          <div class="stat-value">{{ stats.expiring }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 授权列表 -->
    <div v-loading="loading">
      <el-card v-for="license in licenses" :key="license.id" class="license-card">
        <div class="license-header">
          <div>
            <strong>{{ license.bound_to || '未绑定' }}</strong>
            <span class="license-code">{{ license.license_code }}</span>
          </div>
          <el-tag :type="getStatusType(license)" size="large">
            {{ getStatusText(license) }}
          </el-tag>
        </div>

        <el-descriptions :column="2" border class="license-detail">
          <el-descriptions-item label="授权类型">
            {{ license.license_type === 'yearly' ? '年付' : '月付' }}
          </el-descriptions-item>
          <el-descriptions-item label="剩余天数">
            <el-tag :type="getDaysTagType(license.days_remaining)">
              {{ license.days_remaining }} 天
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="激活时间">
            {{ formatDate(license.activated_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="到期时间">
            <span :style="{ color: getExpiryColor(license.expires_at) }">
              {{ formatDate(license.expires_at) }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="自动续费" :span="2">
            <el-switch
              v-model="license.auto_renew"
              @change="handleToggleAutoRenew(license)"
              active-text="已启用"
              inactive-text="已禁用"
            />
          </el-descriptions-item>
        </el-descriptions>

        <div class="license-actions">
          <el-button size="small" @click="showExtendDialog(license)" v-if="license.is_active">
            展期
          </el-button>
          <el-button size="small" type="danger" @click="handleRevoke(license)" v-if="license.is_active">
            撤销
          </el-button>
        </div>
      </el-card>

      <el-empty v-if="licenses.length === 0 && !loading" description="暂无授权，请激活授权码"></el-empty>
    </div>

    <!-- 激活授权码对话框 -->
    <el-dialog v-model="showActivateDialog" title="激活授权码" width="500px">
      <el-form :model="activateForm" label-width="100px">
        <el-form-item label="授权码" required>
          <el-input v-model="activateForm.license_code" placeholder="请输入授权码" />
        </el-form-item>
        <el-form-item label="绑定群ID">
          <el-input v-model="activateForm.bound_to" placeholder="可选，绑定的微信群ID" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showActivateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleActivate" :loading="activating">激活</el-button>
      </template>
    </el-dialog>

    <!-- 展期对话框 -->
    <el-dialog v-model="showExtendDialogVisible" title="授权展期" width="500px">
      <el-form :model="extendForm" label-width="100px">
        <el-form-item label="授权码">
          <el-input v-model="extendForm.license_code" disabled />
        </el-form-item>
        <el-form-item label="当前到期">
          <el-input :value="formatDate(extendForm.current_expiry)" disabled />
        </el-form-item>
        <el-form-item label="展期时长" required>
          <el-select v-model="extendForm.months" placeholder="选择展期时长" style="width: 100%">
            <el-option label="1个月（原价）" :value="1" />
            <el-option label="3个月（95折）" :value="3" />
            <el-option label="6个月（9折）" :value="6" />
            <el-option label="12个月（8折）" :value="12" />
          </el-select>
        </el-form-item>
        <el-form-item label="预估费用">
          <span class="total-price">¥{{ calculateExtendPrice() }}</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showExtendDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleExtend" :loading="extending">确认展期</el-button>
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
  getLicenseStats,
  activateLicense,
  revokeLicense,
  extendLicense,
  toggleAutoRenew
} from '../../../api/desktop/licenses'

// 数据
const licenses = ref([])
const loading = ref(false)
const activating = ref(false)
const extending = ref(false)

// 统计信息
const stats = reactive({
  total: 0,
  active: 0,
  expiring: 0
})

// 激活表单
const showActivateDialog = ref(false)
const activateForm = reactive({
  license_code: '',
  bound_to: ''
})

// 展期表单
const showExtendDialogVisible = ref(false)
const extendForm = reactive({
  id: null,
  license_code: '',
  current_expiry: '',
  months: 1
})

// 加载授权列表
const loadLicenses = async () => {
  loading.value = true
  try {
    const res = await getLicenses()
    if (res.success) {
      licenses.value = res.licenses || []
    } else {
      ElMessage.error(res.error || '加载失败')
    }
  } catch (error) {
    ElMessage.error('加载授权列表失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// 加载统计信息
const loadStats = async () => {
  try {
    const res = await getLicenseStats()
    if (res.success) {
      Object.assign(stats, res.stats)
    }
  } catch (error) {
    console.error('加载统计信息失败', error)
  }
}

// 激活授权码
const handleActivate = async () => {
  if (!activateForm.license_code) {
    ElMessage.warning('请输入授权码')
    return
  }

  activating.value = true
  try {
    const res = await activateLicense(activateForm)
    if (res.success) {
      ElMessage.success('激活成功')
      showActivateDialog.value = false
      activateForm.license_code = ''
      activateForm.bound_to = ''
      loadLicenses()
      loadStats()
    } else {
      ElMessage.error(res.error || '激活失败')
    }
  } catch (error) {
    ElMessage.error('激活失败')
    console.error(error)
  } finally {
    activating.value = false
  }
}

// 显示展期对话框
const showExtendDialog = (license) => {
  extendForm.id = license.id
  extendForm.license_code = license.license_code
  extendForm.current_expiry = license.expires_at
  extendForm.months = 1
  showExtendDialogVisible.value = true
}

// 计算展期价格
const calculateExtendPrice = () => {
  const basePrice = 100 // 基础价格：100元/月
  const discounts = {
    1: 1.0,   // 原价
    3: 0.95,  // 95折
    6: 0.9,   // 9折
    12: 0.8   // 8折
  }
  
  const discount = discounts[extendForm.months] || 1.0
  const total = basePrice * extendForm.months * discount
  return total.toFixed(2)
}

// 执行展期
const handleExtend = async () => {
  extending.value = true
  try {
    const res = await extendLicense(extendForm.id, {
      months: extendForm.months
    })
    
    if (res.success) {
      ElMessage.success(res.message || '展期成功')
      showExtendDialogVisible.value = false
      loadLicenses()
      loadStats()
    } else {
      ElMessage.error(res.error || '展期失败')
    }
  } catch (error) {
    ElMessage.error('展期失败')
    console.error(error)
  } finally {
    extending.value = false
  }
}

// 切换自动续费
const handleToggleAutoRenew = async (license) => {
  try {
    const res = await toggleAutoRenew(license.id, license.auto_renew)
    if (res.success) {
      ElMessage.success(license.auto_renew ? '已启用自动续费' : '已禁用自动续费')
    } else {
      // 恢复原状态
      license.auto_renew = !license.auto_renew
      ElMessage.error(res.error || '操作失败')
    }
  } catch (error) {
    // 恢复原状态
    license.auto_renew = !license.auto_renew
    ElMessage.error('操作失败')
    console.error(error)
  }
}

// 撤销授权
const handleRevoke = async (license) => {
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

    const res = await revokeLicense(license.id)
    if (res.success) {
      ElMessage.success('撤销成功')
      loadLicenses()
      loadStats()
    } else {
      ElMessage.error(res.error || '撤销失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('撤销失败')
      console.error(error)
    }
  }
}

// 工具函数
const getStatusType = (license) => {
  if (!license.is_active) return 'danger'
  if (license.days_remaining <= 7) return 'warning'
  return 'success'
}

const getStatusText = (license) => {
  if (!license.is_active) return '已过期'
  if (license.days_remaining <= 7) return '即将到期'
  return '有效'
}

const getDaysTagType = (days) => {
  if (days < 0) return 'danger'
  if (days <= 7) return 'warning'
  if (days <= 30) return 'info'
  return 'success'
}

const formatDate = (dateStr) => {
  return dateStr ? new Date(dateStr).toLocaleDateString('zh-CN') : '-'
}

const getExpiryColor = (expiresAt) => {
  if (!expiresAt) return '#606266'
  const days = Math.ceil((new Date(expiresAt) - new Date()) / (1000 * 60 * 60 * 24))
  if (days < 0) return '#f56c6c' // 已过期 - 红色
  if (days < 30) return '#e6a23c' // 30天内 - 橙色
  if (days < 90) return '#409eff' // 90天内 - 蓝色
  return '#67c23a' // 正常 - 绿色
}

onMounted(() => {
  loadLicenses()
  loadStats()
})
</script>

<style scoped lang="scss">
.licenses-container {
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;

    h2 {
      margin: 0;
      font-size: 20px;
      color: #1e293b;
    }
  }

  .stats-cards {
    margin-bottom: 20px;
    
    .stat-card {
      text-align: center;
      padding: 20px 0;
      
      &.purple { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #fff; }
      &.green { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: #fff; }
      &.orange { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: #fff; }
      
      .stat-value { font-size: 28px; font-weight: bold; margin-top: 8px; }
      .stat-label { font-size: 14px; opacity: 0.9; }
    }
  }

  .license-card {
    margin-bottom: 15px;
    transition: box-shadow 0.3s;
    
    &:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
    
    .license-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 15px;
      
      .license-code {
        color: #909399;
        font-size: 12px;
        margin-left: 10px;
      }
    }
    
    .license-detail {
      margin-bottom: 15px;
    }
    
    .license-actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      border-top: 1px solid #ebeef5;
      padding-top: 15px;
    }
  }

  .total-price {
    font-size: 20px;
    color: #f56c6c;
    font-weight: bold;
  }
}
</style>

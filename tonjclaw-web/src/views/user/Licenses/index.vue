<template>
  <div class="user-licenses">
    <div class="header-actions">
      <h2 class="section-title">授权码管理</h2>
      <el-button type="primary" @click="showBuyLicense = true">
        <el-icon><Plus /></el-icon> 购买授权
      </el-button>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-grid">
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card purple">
          <div class="stat-label">总授权数</div>
          <div class="stat-value">{{ licenseStats.total }}</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card green">
          <div class="stat-label">有效授权</div>
          <div class="stat-value">{{ licenseStats.active }}</div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card orange">
          <div class="stat-label">即将到期</div>
          <div class="stat-value">{{ licenseStats.expiring }}</div>
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
          <el-tag :type="getStatusType(license)">{{ getStatusText(license) }}</el-tag>
        </div>
        <el-descriptions :column="2" border size="small" class="license-detail">
          <el-descriptions-item label="类型">{{ license.license_type === 'monthly' ? '月付' : '年付' }}</el-descriptions-item>
          <el-descriptions-item label="激活时间">{{ formatDate(license.activated_at) }}</el-descriptions-item>
          <el-descriptions-item label="到期时间">{{ formatDate(license.expires_at) }}</el-descriptions-item>
          <el-descriptions-item label="剩余天数">{{ license.days_remaining || 0 }} 天</el-descriptions-item>
          <el-descriptions-item label="销售员" v-if="license.salesperson">
            {{ license.salesperson.name }} <span v-if="license.salesperson.phone">({{ license.salesperson.phone }})</span>
          </el-descriptions-item>
          <el-descriptions-item label="自动续费">
            <el-tag :type="license.auto_renew ? 'success' : 'info'" size="small">
              {{ license.auto_renew ? `已启用 (${license.renew_period})` : '未启用' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
        <div class="license-actions">
          <el-button size="small" @click="renewLicense(license)">续期</el-button>
          <el-button size="small" type="primary" @click="selectForExtension(license)" v-if="license.is_active">批量展期</el-button>
          <el-button size="small" :type="license.auto_renew ? 'warning' : 'success'" @click="toggleAutoRenew(license)">
            {{ license.auto_renew ? '禁用自动续费' : '启用自动续费' }}
          </el-button>
          <el-button size="small" type="danger" @click="revokeLicense(license)">撤销</el-button>
        </div>
      </el-card>

      <el-empty v-if="licenses.length === 0 && !loading" description="暂无授权,点击购买"></el-empty>
    </div>

    <!-- 购买授权对话框 -->
    <el-dialog v-model="showBuyLicense" title="购买授权" width="500px">
      <el-form :model="buyForm" label-width="100px">
        <el-form-item label="授权类型">
          <el-radio-group v-model="buyForm.type">
            <el-radio label="monthly">月付 (¥80/群)</el-radio>
            <el-radio label="yearly">年付 (¥600/群,省¥360)</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="微信群ID">
          <el-input v-model="buyForm.group_id" placeholder="请输入要授权的微信群ID"></el-input>
        </el-form-item>
        <el-form-item label="数量">
          <el-input-number v-model="buyForm.quantity" :min="1" :max="10"></el-input-number>
        </el-form-item>
        <el-form-item label="总计">
          <span class="total-price">¥{{ calculateTotal }}</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showBuyLicense = false">取消</el-button>
        <el-button type="primary" @click="handlePurchase">立即购买</el-button>
      </template>
    </el-dialog>

    <!-- 批量展期对话框 -->
    <el-dialog v-model="showBatchExtend" title="授权码批量展期" width="600px">
      <div style="margin-bottom: 20px;">
        <p>已选择 <strong>{{ selectedLicenses.length }}</strong> 个授权码进行展期</p>
        <el-table :data="selectedLicenses" style="width: 100%; margin-top: 10px;" max-height="200">
          <el-table-column prop="license_code" label="授权码"></el-table-column>
          <el-table-column prop="bound_to" label="绑定群"></el-table-column>
        </el-table>
      </div>
      
      <el-form label-width="100px">
        <el-form-item label="展期周期">
          <el-radio-group v-model="extendPeriod">
            <el-radio label="1m">1个月 (原价)</el-radio>
            <el-radio label="3m">3个月 (95折)</el-radio>
            <el-radio label="6m">6个月 (9折)</el-radio>
            <el-radio label="1y">1年 (8折)</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="预估费用">
          <span class="total-price">¥{{ estimatedCost }}</span>
        </el-form-item>
        <el-form-item label="自动续费">
          <el-switch v-model="enableAutoRenew" active-text="启用" inactive-text="禁用"></el-switch>
          <div v-if="enableAutoRenew" style="margin-top: 10px;">
            <el-radio-group v-model="autoRenewPeriod">
              <el-radio label="1m">每月</el-radio>
              <el-radio label="3m">每3月</el-radio>
              <el-radio label="6m">每6月</el-radio>
              <el-radio label="1y">每年</el-radio>
            </el-radio-group>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showBatchExtend = false">取消</el-button>
        <el-button type="primary" @click="handleBatchExtend" :loading="extending">确认支付并展期</el-button>
      </template>
    </el-dialog>

    <!-- 自动续费设置对话框 -->
    <el-dialog v-model="showAutoRenewDialog" title="设置自动续费" width="500px">
      <div v-if="currentLicenseForRenew">
        <p>授权码: <strong>{{ currentLicenseForRenew.license_code }}</strong></p>
        <p>当前状态: 
          <el-tag :type="currentLicenseForRenew.auto_renew ? 'success' : 'info'" size="small">
            {{ currentLicenseForRenew.auto_renew ? `已启用 (${currentLicenseForRenew.renew_period})` : '未启用' }}
          </el-tag>
        </p>
        
        <el-form label-width="100px" style="margin-top: 20px;">
          <el-form-item label="续费周期">
            <el-radio-group v-model="autoRenewPeriodForm">
              <el-radio label="1m">1个月</el-radio>
              <el-radio label="3m">3个月 (95折)</el-radio>
              <el-radio label="6m">6个月 (9折)</el-radio>
              <el-radio label="1y">1年 (8折)</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <el-button @click="showAutoRenewDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmAutoRenewSetting" :loading="autoRenewLoading">
          {{ currentLicenseForRenew?.auto_renew ? '禁用自动续费' : '启用自动续费' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import request from '../../../utils/request'

const loading = ref(false)
const licenses = ref([])
const licenseStats = reactive({ total: 0, active: 0, expiring: 0 })

// 购买相关
const showBuyLicense = ref(false)
const buyForm = reactive({ type: 'yearly', group_id: '', quantity: 1 })
const calculateTotal = computed(() => (buyForm.type === 'yearly' ? 600 : 80) * buyForm.quantity)

// 批量展期相关
const showBatchExtend = ref(false)
const selectedLicenses = ref([])
const extendPeriod = ref('1m')
const extending = ref(false)
const enableAutoRenew = ref(false)
const autoRenewPeriod = ref('1m')
const basePrice = 100 // 默认单价，实际应从后端获取或根据套餐计算
const estimatedCost = computed(() => {
  if (!selectedLicenses.value.length) return 0
  const discountMap = { '1m': 1.0, '3m': 0.95, '6m': 0.90, '1y': 0.80 }
  const monthMap = { '1m': 1, '3m': 3, '6m': 6, '1y': 12 }
  const count = selectedLicenses.value.length
  const months = monthMap[extendPeriod.value]
  const discount = discountMap[extendPeriod.value]
  return (count * basePrice * months * discount).toFixed(2)
})

// 自动续费相关
const showAutoRenewDialog = ref(false)
const currentLicenseForRenew = ref(null)
const autoRenewPeriodForm = ref('1m')
const autoRenewLoading = ref(false)

const loadLicenses = async () => {
  loading.value = true
  try {
    const res = await request.get('/api/license/list', { params: { active_only: false } })
    if (res.success) {
      licenses.value = res.licenses || []
      updateStats()
    }
  } catch (error) {
    console.error('加载授权列表失败:', error)
  } finally {
    loading.value = false
  }
}

const updateStats = () => {
  licenseStats.total = licenses.value.length
  licenseStats.active = licenses.value.filter(l => l.is_active).length
  licenseStats.expiring = licenses.value.filter(l => l.is_active && l.days_remaining <= 7).length
}

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

const formatDate = (dateStr) => dateStr ? new Date(dateStr).toLocaleDateString('zh-CN') : '-'

const handlePurchase = async () => {
  if (!buyForm.group_id) {
    ElMessage.warning('请填写微信群ID')
    return
  }
  try {
    const res = await request.post('/api/pricing/purchase', {
      ...buyForm,
      amount: calculateTotal.value
    })
    if (res.success) {
      ElMessage.success('购买成功，请前往支付页面完成付款')
      showBuyLicense.value = false
      loadLicenses()
    } else {
      ElMessage.error(res.error || '购买失败')
    }
  } catch (error) {
    const errorMsg = error.response?.data?.error || error.message || '网络请求失败'
    ElMessage.error(errorMsg)
  }
}

const renewLicense = (license) => {
  ElMessage.info('单个续期功能开发中，建议使用批量展期')
}

const selectForExtension = (license) => {
  selectedLicenses.value = [license]
  showBatchExtend.value = true
}

const handleBatchExtend = async () => {
  if (selectedLicenses.value.length === 0) return
  
  extending.value = true
  try {
    const licenseIds = selectedLicenses.value.map(l => l.id)
    const res = await request.post('/api/pricing/licenses/extend', {
      license_ids: licenseIds,
      period: extendPeriod.value,
      enable_auto_renew: enableAutoRenew.value,
      auto_renew_period: enableAutoRenew.value ? autoRenewPeriod.value : undefined
    })
    
    if (res.success) {
      ElMessage.success(res.message || '展期成功')
      showBatchExtend.value = false
      enableAutoRenew.value = false
      loadLicenses()
    } else {
      ElMessage.error(res.error || '展期失败')
    }
  } catch (error) {
    const errorMsg = error.response?.data?.error || error.message || '网络请求失败'
    ElMessage.error(errorMsg)
  } finally {
    extending.value = false
  }
}

const revokeLicense = async (license) => {
  try {
    await ElMessageBox.confirm('确定要撤销此授权吗?撤销后立即失效。', '警告', { type: 'warning' })
    const res = await request.post(`/api/license/${license.id}/revoke`)
    if (res.success) {
      ElMessage.success('撤销成功')
      loadLicenses()
    } else {
      ElMessage.error(res.error || '撤销失败')
    }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('操作失败')
  }
}

const toggleAutoRenew = (license) => {
  currentLicenseForRenew.value = license
  autoRenewPeriodForm.value = license.renew_period || '1m'
  showAutoRenewDialog.value = true
}

const confirmAutoRenewSetting = async () => {
  if (!currentLicenseForRenew.value) return
  
  autoRenewLoading.value = true
  try {
    let res
    if (currentLicenseForRenew.value.auto_renew) {
      res = await request.post('/api/auto-renew/disable', { license_id: currentLicenseForRenew.value.id })
    } else {
      res = await request.post('/api/auto-renew/enable', {
        license_id: currentLicenseForRenew.value.id,
        renew_period: autoRenewPeriodForm.value
      })
    }
    
    if (res.success) {
      ElMessage.success(res.message || '操作成功')
      showAutoRenewDialog.value = false
      loadLicenses()
    } else {
      ElMessage.error(res.error || '操作失败')
    }
  } catch (error) {
    ElMessage.error('网络请求失败')
  } finally {
    autoRenewLoading.value = false
  }
}

onMounted(() => {
  loadLicenses()
})
</script>

<style scoped lang="scss">
.user-licenses {
  .header-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    
    .section-title {
      margin: 0;
      font-size: 20px;
      color: #1e293b;
    }
  }

  .stats-grid {
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

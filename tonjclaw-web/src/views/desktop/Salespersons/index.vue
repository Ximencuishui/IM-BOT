<template>
  <div class="salespersons-page">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-cards">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-icon" style="background-color: #3b82f6">
              <el-icon><User /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ stats.total_count || 0 }}</div>
              <div class="stat-label">销售人员总数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-icon" style="background-color: #10b981">
              <el-icon><CircleCheck /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ stats.active_count || 0 }}</div>
              <div class="stat-label">在职人员</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-icon" style="background-color: #f59e0b">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ stats.total_sales || 0 }}</div>
              <div class="stat-label">累计订单数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-icon" style="background-color: #8b5cf6">
              <el-icon><Coin /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">¥{{ stats.total_amount || 0 }}</div>
              <div class="stat-label">累计销售额</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 搜索和操作栏 -->
    <el-card class="search-card">
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="关键词">
          <el-input v-model="searchForm.keyword" placeholder="姓名/电话" clearable />
        </el-form-item>
        <el-form-item label="线路">
          <el-select v-model="searchForm.route_id" placeholder="全部线路" clearable>
            <el-option
              v-for="route in routeList"
              :key="route.id"
              :label="route.route_name"
              :value="route.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.is_active" placeholder="全部" clearable>
            <el-option label="在职" value="true" />
            <el-option label="离职" value="false" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
      
      <div class="action-buttons">
        <el-button type="success" @click="showCreateDialog">
          <el-icon><Plus /></el-icon>
          新增销售人员
        </el-button>
      </div>
    </el-card>

    <!-- 销售人员表格 -->
    <el-card class="table-card">
      <el-table
        v-loading="loading"
        :data="salespersonList"
        border
        stripe
        style="width: 100%"
      >
        <el-table-column prop="name" label="姓名" width="120" />
        <el-table-column prop="phone" label="电话" width="130" />
        <el-table-column prop="region" label="负责区域" width="120" />
        <el-table-column prop="route_name" label="所属线路" width="120" />
        <el-table-column label="授权码" min-width="150">
          <template #default="{ row }">
            <el-tag
              v-for="(code, index) in row.license_codes"
              :key="index"
              size="small"
              style="margin-right: 5px; margin-bottom: 5px"
            >
              {{ code }}
            </el-tag>
            <span v-if="!row.license_codes || row.license_codes.length === 0" style="color: #94a3b8">
              未分配
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="total_sales" label="累计订单" width="100" />
        <el-table-column prop="total_amount" label="累计销售额" width="120">
          <template #default="{ row }">
            ¥{{ row.total_amount }}
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '在职' : '离职' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showEditDialog(row)">
              编辑
            </el-button>
            <el-button link type="warning" size="small" @click="showLicenseDialog(row)">
              授权码
            </el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑销售人员' : '新增销售人员'"
      width="600px"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="姓名" prop="name">
          <el-input v-model="formData.name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="电话" prop="phone">
          <el-input v-model="formData.phone" placeholder="请输入电话号码" />
        </el-form-item>
        <el-form-item label="负责区域">
          <el-input v-model="formData.region" placeholder="例如：朝阳区、海淀区" />
        </el-form-item>
        <el-form-item label="所属线路">
          <el-select v-model="formData.route_id" placeholder="请选择线路" style="width: 100%" clearable>
            <el-option
              v-for="route in routeList"
              :key="route.id"
              :label="route.route_name"
              :value="route.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="formData.remark" type="textarea" :rows="3" placeholder="请输入备注信息" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="formData.is_active" active-text="在职" inactive-text="离职" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 授权码管理对话框 -->
    <el-dialog v-model="licenseDialogVisible" title="管理授权码" width="600px">
      <div v-if="currentSalesperson" class="license-management">
        <el-alert
          :title="`销售人员：${currentSalesperson.name}`"
          type="info"
          :closable="false"
          style="margin-bottom: 20px"
        />

        <el-form label-width="100px">
          <el-form-item label="当前授权码">
            <div class="current-licenses">
              <el-tag
                v-for="(code, index) in currentLicenses"
                :key="index"
                closable
                @close="removeLicense(code)"
                style="margin-right: 10px; margin-bottom: 10px"
              >
                {{ code }}
              </el-tag>
              <span v-if="currentLicenses.length === 0" style="color: #94a3b8">
                暂未分配授权码
              </span>
            </div>
          </el-form-item>
          <el-form-item label="添加授权码">
            <el-input
              v-model="newLicenseCode"
              placeholder="输入授权码后按回车"
              @keyup.enter="addLicense"
            >
              <template #append>
                <el-button @click="addLicense">添加</el-button>
              </template>
            </el-input>
            <div class="form-tip">输入授权码后按回车或点击添加按钮</div>
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <el-button @click="licenseDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="saveLicenses" :loading="savingLicenses">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getSalespersons, createSalesperson, updateSalesperson, deleteSalesperson, assignLicenses, getSalespersonStats } from '../../../api/desktop/salespersons'
import { getRoutes } from '../../../api/desktop/customers'

const loading = ref(false)
const salespersonList = ref([])
const routeList = ref([])
const dialogVisible = ref(false)
const licenseDialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const savingLicenses = ref(false)
const currentSalesperson = ref(null)
const currentLicenses = ref([])
const newLicenseCode = ref('')
const formRef = ref(null)

const stats = ref({
  total_count: 0,
  active_count: 0,
  total_sales: 0,
  total_amount: 0
})

const searchForm = reactive({
  keyword: '',
  route_id: null,
  is_active: null
})

const formData = reactive({
  id: null,
  name: '',
  phone: '',
  region: '',
  route_id: null,
  remark: '',
  is_active: true
})

const formRules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  phone: [
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ]
}

// 加载销售人员列表
const loadSalespersons = async () => {
  loading.value = true
  try {
    const params = {
      keyword: searchForm.keyword,
      route_id: searchForm.route_id,
      is_active: searchForm.is_active
    }

    const res = await getSalespersons(params)
    if (res.success) {
      salespersonList.value = res.salespersons || []
    }
  } catch (error) {
    ElMessage.error('加载销售人员失败')
  } finally {
    loading.value = false
  }
}

// 加载统计数据
const loadStats = async () => {
  try {
    const res = await getSalespersonStats()
    if (res.success) {
      stats.value = res.stats || {}
    }
  } catch (error) {
    console.error('加载统计数据失败', error)
  }
}

// 加载线路列表
const loadRoutes = async () => {
  try {
    const res = await getRoutes()
    if (res.success) {
      routeList.value = res.routes || []
    }
  } catch (error) {
    console.error('加载线路失败', error)
  }
}

// 搜索
const handleSearch = () => {
  loadSalespersons()
}

// 重置
const handleReset = () => {
  searchForm.keyword = ''
  searchForm.route_id = null
  searchForm.is_active = null
  handleSearch()
}

// 显示创建对话框
const showCreateDialog = () => {
  isEdit.value = false
  resetForm()
  dialogVisible.value = true
}

// 显示编辑对话框
const showEditDialog = (salesperson) => {
  isEdit.value = true
  Object.assign(formData, {
    id: salesperson.id,
    name: salesperson.name,
    phone: salesperson.phone || '',
    region: salesperson.region || '',
    route_id: salesperson.route_id,
    remark: salesperson.remark || '',
    is_active: salesperson.is_active
  })
  dialogVisible.value = true
}

// 重置表单
const resetForm = () => {
  Object.assign(formData, {
    id: null,
    name: '',
    phone: '',
    region: '',
    route_id: null,
    remark: '',
    is_active: true
  })
  formRef.value?.clearValidate()
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    submitting.value = true
    try {
      const data = { ...formData }
      
      if (isEdit.value) {
        await updateSalesperson(formData.id, data)
        ElMessage.success('更新成功')
      } else {
        await createSalesperson(data)
        ElMessage.success('创建成功')
      }
      
      dialogVisible.value = false
      loadSalespersons()
      loadStats()
    } catch (error) {
      ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
    } finally {
      submitting.value = false
    }
  })
}

// 删除销售人员
const handleDelete = (salesperson) => {
  ElMessageBox.confirm(`确定要删除销售人员"${salesperson.name}"吗?`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await deleteSalesperson(salesperson.id)
      ElMessage.success('删除成功')
      loadSalespersons()
      loadStats()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
}

// 显示授权码管理对话框
const showLicenseDialog = (salesperson) => {
  currentSalesperson.value = salesperson
  currentLicenses.value = [...(salesperson.license_codes || [])]
  newLicenseCode.value = ''
  licenseDialogVisible.value = true
}

// 添加授权码
const addLicense = () => {
  const code = newLicenseCode.value.trim()
  if (!code) {
    ElMessage.warning('请输入授权码')
    return
  }
  
  if (currentLicenses.value.includes(code)) {
    ElMessage.warning('该授权码已存在')
    return
  }
  
  currentLicenses.value.push(code)
  newLicenseCode.value = ''
}

// 移除授权码
const removeLicense = (code) => {
  const index = currentLicenses.value.indexOf(code)
  if (index > -1) {
    currentLicenses.value.splice(index, 1)
  }
}

// 保存授权码
const saveLicenses = async () => {
  savingLicenses.value = true
  try {
    await assignLicenses(currentSalesperson.value.id, currentLicenses.value)
    ElMessage.success('保存成功')
    licenseDialogVisible.value = false
    loadSalespersons()
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    savingLicenses.value = false
  }
}

onMounted(() => {
  loadSalespersons()
  loadStats()
  loadRoutes()
})
</script>

<style scoped lang="scss">
.salespersons-page {
  .stats-cards {
    margin-bottom: 20px;
    
    .stat-item {
      display: flex;
      align-items: center;
      gap: 15px;
      
      .stat-icon {
        width: 50px;
        height: 50px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #fff;
        font-size: 24px;
      }
      
      .stat-content {
        flex: 1;
        
        .stat-value {
          font-size: 24px;
          font-weight: bold;
          color: #1e293b;
        }
        
        .stat-label {
          font-size: 14px;
          color: #64748b;
          margin-top: 4px;
        }
      }
    }
  }

  .search-card {
    margin-bottom: 20px;
    
    .search-form {
      margin-bottom: 10px;
    }
    
    .action-buttons {
      display: flex;
      gap: 10px;
    }
  }

  .table-card {
    .pagination {
      margin-top: 20px;
      display: flex;
      justify-content: flex-end;
    }
  }

  .license-management {
    .current-licenses {
      min-height: 40px;
      padding: 10px;
      background-color: #f8fafc;
      border-radius: 6px;
    }
    
    .form-tip {
      font-size: 12px;
      color: #94a3b8;
      margin-top: 5px;
    }
  }
}
</style>

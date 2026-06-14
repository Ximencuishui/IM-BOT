<template>
  <div class="customers-page">
    <!-- 搜索和操作栏 -->
    <el-card class="search-card">
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="客户名称">
          <el-input v-model="searchForm.name" placeholder="输入客户名称" clearable />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="searchForm.phone" placeholder="输入电话号码" clearable />
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
        <el-form-item label="销售">
          <el-input v-model="searchForm.sales_person" placeholder="输入销售人员" clearable />
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
          新增客户
        </el-button>
        <el-button type="warning" @click="showImportDialog">
          <el-icon><Upload /></el-icon>
          导入客户
        </el-button>
        <el-button type="info" @click="handleExport">
          <el-icon><Download /></el-icon>
          导出客户
        </el-button>
      </div>
    </el-card>

    <!-- 客户表格 -->
    <el-card class="table-card">
      <el-table
        v-loading="loading"
        :data="customerList"
        border
        stripe
        style="width: 100%"
      >
        <el-table-column prop="customer_name" label="客户名称" min-width="120" />
        <el-table-column prop="phone" label="电话" width="130" />
        <el-table-column prop="address" label="地址" min-width="200" show-overflow-tooltip />
        <el-table-column prop="route_name" label="线路" width="100" />
        <el-table-column prop="sales_person" label="销售" width="100" />
        <el-table-column prop="wx_group_id" label="微信群ID" width="150" show-overflow-tooltip />
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="showEditDialog(row)">
              编辑
            </el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadCustomers"
          @current-change="loadCustomers"
        />
      </div>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑客户' : '新增客户'"
      width="600px"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="客户名称" prop="customer_name">
          <el-input v-model="formData.customer_name" placeholder="请输入客户名称" />
        </el-form-item>
        <el-form-item label="电话" prop="phone">
          <el-input v-model="formData.phone" placeholder="请输入电话号码" />
        </el-form-item>
        <el-form-item label="地址">
          <el-input v-model="formData.address" type="textarea" :rows="2" placeholder="请输入详细地址" />
        </el-form-item>
        <el-form-item label="所属线路" prop="route_id">
          <el-select v-model="formData.route_id" placeholder="请选择线路" style="width: 100%">
            <el-option
              v-for="route in routeList"
              :key="route.id"
              :label="route.route_name"
              :value="route.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="销售人员">
          <el-input v-model="formData.sales_person" placeholder="请输入销售人员姓名" />
        </el-form-item>
        <el-form-item label="微信群ID">
          <el-input v-model="formData.wx_group_id" placeholder="请输入微信群ID" />
          <div class="form-tip">用于自动识别客户订单</div>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="formData.remark" type="textarea" :rows="3" placeholder="请输入备注信息" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="formData.is_active" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 导入对话框 -->
    <el-dialog v-model="importDialogVisible" title="导入客户" width="500px">
      <el-upload
        ref="uploadRef"
        drag
        :auto-upload="false"
        :on-change="handleFileChange"
        :limit="1"
        accept=".xlsx,.xls,.csv"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          将文件拖到此处，或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 Excel (.xlsx, .xls) 或 CSV 格式
          </div>
        </template>
      </el-upload>

      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleImport" :loading="importing" :disabled="!selectedFile">
          开始导入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getCustomers, createCustomer, updateCustomer, deleteCustomer, importCustomers, exportCustomers, getRoutes } from '../../../api/desktop/customers'

const loading = ref(false)
const customerList = ref([])
const routeList = ref([])
const dialogVisible = ref(false)
const importDialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const importing = ref(false)
const selectedFile = ref(null)
const formRef = ref(null)
const uploadRef = ref(null)

const searchForm = reactive({
  name: '',
  phone: '',
  route_id: null,
  sales_person: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const formData = reactive({
  id: null,
  customer_name: '',
  phone: '',
  address: '',
  route_id: null,
  sales_person: '',
  wx_group_id: '',
  remark: '',
  is_active: true
})

const formRules = {
  customer_name: [{ required: true, message: '请输入客户名称', trigger: 'blur' }],
  phone: [
    { required: true, message: '请输入电话号码', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号', trigger: 'blur' }
  ],
  route_id: [{ required: true, message: '请选择线路', trigger: 'change' }]
}

// 加载客户列表
const loadCustomers = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
      route_id: searchForm.route_id,
      sales_person: searchForm.sales_person
    }
    
    if (searchForm.name) {
      params.name = searchForm.name
    }
    if (searchForm.phone) {
      params.phone = searchForm.phone
    }

    const res = await getCustomers(params)
    if (res.success) {
      customerList.value = res.customers || []
      pagination.total = res.count || 0
    }
  } catch (error) {
    ElMessage.error('加载客户失败')
  } finally {
    loading.value = false
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
  pagination.page = 1
  loadCustomers()
}

// 重置
const handleReset = () => {
  searchForm.name = ''
  searchForm.phone = ''
  searchForm.route_id = null
  searchForm.sales_person = ''
  handleSearch()
}

// 显示创建对话框
const showCreateDialog = () => {
  isEdit.value = false
  resetForm()
  dialogVisible.value = true
}

// 显示编辑对话框
const showEditDialog = (customer) => {
  isEdit.value = true
  Object.assign(formData, {
    id: customer.id,
    customer_name: customer.customer_name,
    phone: customer.phone,
    address: customer.address || '',
    route_id: customer.route_id,
    sales_person: customer.sales_person || '',
    wx_group_id: customer.wx_group_id || '',
    remark: customer.remark || '',
    is_active: customer.is_active
  })
  dialogVisible.value = true
}

// 重置表单
const resetForm = () => {
  Object.assign(formData, {
    id: null,
    customer_name: '',
    phone: '',
    address: '',
    route_id: null,
    sales_person: '',
    wx_group_id: '',
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
        await updateCustomer(formData.id, data)
        ElMessage.success('更新成功')
      } else {
        await createCustomer(data)
        ElMessage.success('创建成功')
      }
      
      dialogVisible.value = false
      loadCustomers()
    } catch (error) {
      ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
    } finally {
      submitting.value = false
    }
  })
}

// 删除客户
const handleDelete = (customer) => {
  ElMessageBox.confirm(`确定要删除客户"${customer.customer_name}"吗?`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await deleteCustomer(customer.id)
      ElMessage.success('删除成功')
      loadCustomers()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
}

// 显示导入对话框
const showImportDialog = () => {
  selectedFile.value = null
  importDialogVisible.value = true
}

// 文件选择
const handleFileChange = (file) => {
  selectedFile.value = file.raw
}

// 导入客户
const handleImport = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请选择文件')
    return
  }

  importing.value = true
  try {
    await importCustomers(selectedFile.value)
    ElMessage.success('导入成功')
    importDialogVisible.value = false
    loadCustomers()
  } catch (error) {
    ElMessage.error('导入失败')
  } finally {
    importing.value = false
  }
}

// 导出客户
const handleExport = async () => {
  try {
    const params = {}
    if (searchForm.route_id) {
      params.route_id = searchForm.route_id
    }
    
    const res = await exportCustomers(params)
    const blob = new Blob([res], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `客户列表_${new Date().toISOString().split('T')[0]}.xlsx`
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

onMounted(() => {
  loadCustomers()
  loadRoutes()
})
</script>

<style scoped lang="scss">
.customers-page {
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

  .form-tip {
    font-size: 12px;
    color: #94a3b8;
    margin-top: 5px;
  }
}
</style>

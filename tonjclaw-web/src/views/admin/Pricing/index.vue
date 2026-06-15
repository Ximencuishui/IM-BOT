<template>
  <div class="pricing-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>定价配置管理</h2>
    </div>

    <!-- 套餐管理 -->
    <el-card class="packages-card">
      <template #header>
        <div class="card-header">
          <span>套餐配置</span>
          <el-button type="primary" size="small" @click="showAddPackage = true">
            <el-icon><Plus /></el-icon> 添加套餐
          </el-button>
        </div>
      </template>

      <el-table 
        :data="packages" 
        style="width: 100%" 
        v-loading="packagesLoading"
      >
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="package_name" label="套餐名称" width="150" />
        <el-table-column label="包含桌面端" width="110">
          <template #default="{ row }">
            <el-tag :type="row.includes_desktop ? 'success' : 'info'">
              {{ row.includes_desktop ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="license_count" label="授权码数量" width="110" />
        <el-table-column prop="validity_months" label="有效期(月)" width="110" />
        <el-table-column prop="price" label="价格(元)" width="110">
          <template #default="{ row }">
            ¥{{ row.price.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sort_order" label="排序" width="80" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="handleEditPackage(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDeletePackage(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加/编辑套餐对话框 -->
    <el-dialog 
      v-model="showAddPackage" 
      :title="editingPackage ? '编辑套餐' : '添加套餐'" 
      width="600px"
    >
      <el-form :model="packageForm" label-width="120px">
        <el-form-item label="套餐名称" required>
          <el-input v-model="packageForm.package_name" placeholder="请输入套餐名称" />
        </el-form-item>
        <el-form-item label="包含桌面端">
          <el-switch v-model="packageForm.includes_desktop" />
          <span class="form-tip" style="margin-left: 10px;">
            {{ packageForm.includes_desktop ? '包含桌面端年费' : '仅授权码' }}
          </span>
        </el-form-item>
        <el-form-item label="授权码数量">
          <el-input-number 
            v-model="packageForm.license_count" 
            :min="0" 
            :max="100"
            controls-position="right"
          />
        </el-form-item>
        <el-form-item label="有效期(月)">
          <el-input-number 
            v-model="packageForm.validity_months" 
            :min="1" 
            :max="36"
            controls-position="right"
          />
        </el-form-item>
        <el-form-item label="价格(元)" required>
          <el-input-number 
            v-model="packageForm.price" 
            :min="0" 
            :step="10"
            :precision="2"
            controls-position="right"
          />
        </el-form-item>
        <el-form-item label="套餐描述">
          <el-input 
            v-model="packageForm.description" 
            type="textarea" 
            :rows="3"
            placeholder="请输入套餐描述"
          />
        </el-form-item>
        <el-form-item label="排序顺序">
          <el-input-number 
            v-model="packageForm.sort_order" 
            :min="0"
            controls-position="right"
          />
          <span class="form-tip" style="margin-left: 10px;">数字越小越靠前</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddPackage = false">取消</el-button>
        <el-button type="primary" @click="handleSavePackage" :loading="savingPackage">
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { 
  getPackages,
  createPackage,
  updatePackage,
  deletePackage
} from '@/api/admin/pricing'

// 套餐管理
const packages = ref([])
const packagesLoading = ref(false)
const showAddPackage = ref(false)
const editingPackage = ref(null)
const savingPackage = ref(false)
const packageForm = reactive({
  package_name: '',
  includes_desktop: false,
  license_count: 1,
  validity_months: 1,
  price: 0,
  description: '',
  sort_order: 0
})

// 加载套餐列表
const loadPackages = async () => {
  packagesLoading.value = true
  try {
    const response = await getPackages()
    if (response.success) {
      packages.value = response.packages || []
    }
  } catch (error) {
    ElMessage.error('加载套餐列表失败')
    console.error(error)
  } finally {
    packagesLoading.value = false
  }
}

// 编辑套餐
const handleEditPackage = (pkg) => {
  editingPackage.value = pkg
  Object.assign(packageForm, {
    package_name: pkg.package_name,
    includes_desktop: pkg.includes_desktop,
    license_count: pkg.license_count,
    validity_months: pkg.validity_months,
    price: pkg.price,
    description: pkg.description || '',
    sort_order: pkg.sort_order || 0
  })
  showAddPackage.value = true
}

// 保存套餐
const handleSavePackage = async () => {
  if (!packageForm.package_name) {
    ElMessage.warning('请输入套餐名称')
    return
  }
  if (packageForm.price <= 0) {
    ElMessage.warning('请输入有效的价格')
    return
  }

  savingPackage.value = true
  try {
    let response
    if (editingPackage.value) {
      // 更新
      response = await updatePackage(editingPackage.value.id, packageForm)
    } else {
      // 创建
      response = await createPackage(packageForm)
    }
    
    if (response.success) {
      ElMessage.success(editingPackage.value ? '套餐更新成功' : '套餐创建成功')
      showAddPackage.value = false
      editingPackage.value = null
      resetPackageForm()
      loadPackages()
    } else {
      ElMessage.error(response.error || '保存失败')
    }
  } catch (error) {
    ElMessage.error('保存失败')
    console.error(error)
  } finally {
    savingPackage.value = false
  }
}

// 删除套餐
const handleDeletePackage = async (pkg) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除套餐 "${pkg.package_name}" 吗？`,
      '确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const response = await deletePackage(pkg.id)
    if (response.success) {
      ElMessage.success('套餐已删除')
      loadPackages()
    } else {
      ElMessage.error(response.error || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
      console.error(error)
    }
  }
}

// 重置套餐表单
const resetPackageForm = () => {
  Object.assign(packageForm, {
    package_name: '',
    includes_desktop: false,
    license_count: 1,
    validity_months: 1,
    price: 0,
    description: '',
    sort_order: 0
  })
}

// 初始化
onMounted(() => {
  loadPackages()
})
</script>

<style scoped>
.pricing-container {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.packages-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-left: 10px;
}
</style>

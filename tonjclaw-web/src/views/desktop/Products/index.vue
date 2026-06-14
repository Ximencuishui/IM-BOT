<template>
  <div class="products-page">
    <!-- 搜索和操作栏 -->
    <el-card class="search-card">
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="商品名称">
          <el-input v-model="searchForm.keyword" placeholder="输入商品名称或编码" clearable />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="searchForm.category" placeholder="全部分类" clearable>
            <el-option label="蔬菜" value="蔬菜" />
            <el-option label="水果" value="水果" />
            <el-option label="肉类" value="肉类" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.is_active" placeholder="全部" clearable>
            <el-option label="启用" :value="1" />
            <el-option label="禁用" :value="0" />
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
          新增商品
        </el-button>
        <el-button type="primary" @click="showCategoryDialog">
          <el-icon><FolderAdd /></el-icon>
          添加分类
        </el-button>
        <el-button type="info" @click="showAttributeDialog">
          <el-icon><Setting /></el-icon>
          添加商品公共属性
        </el-button>
        <el-button type="warning" @click="handleBatchEnable" :disabled="selectedIds.length === 0">
          批量启用
        </el-button>
        <el-button type="danger" @click="handleBatchDisable" :disabled="selectedIds.length === 0">
          批量禁用
        </el-button>
      </div>
    </el-card>

    <!-- 商品表格 -->
    <el-card class="table-card">
      <el-table
        v-loading="loading"
        :data="productList"
        border
        stripe
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="product_name" label="商品名称" min-width="150" />
        <el-table-column prop="product_code" label="商品编码" width="120" />
        <el-table-column label="快捷码" min-width="150">
          <template #default="{ row }">
            <el-tag v-for="(code, index) in row.shortcut_codes" :key="index" size="small" style="margin-right: 5px">
              {{ code }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="unit" label="单位" width="80" />
        <el-table-column prop="price" label="价格" width="100">
          <template #default="{ row }">
            ¥{{ row.price }}
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="100" />
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
          @size-change="loadProducts"
          @current-change="loadProducts"
        />
      </div>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑商品' : '新增商品'"
      width="600px"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="商品名称" prop="product_name">
          <el-input v-model="formData.product_name" placeholder="请输入商品名称" />
        </el-form-item>
        <el-form-item label="商品编码" prop="product_code">
          <el-input v-model="formData.product_code" placeholder="请输入商品编码" />
        </el-form-item>
        <el-form-item label="快捷码">
          <el-select
            v-model="formData.shortcut_codes"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入快捷码后按回车"
            style="width: 100%"
          >
            <el-option
              v-for="item in formData.shortcut_codes"
              :key="item"
              :label="item"
              :value="item"
            />
          </el-select>
          <div class="form-tip">支持多个快捷码，用于快速识别商品</div>
        </el-form-item>
        <el-form-item label="单位" prop="unit">
          <el-select v-model="formData.unit" placeholder="例如：斤、个、箱" style="width: 100%">
            <el-option v-for="u in units" :key="u" :label="u" :value="u" />
          </el-select>
        </el-form-item>
        <el-form-item label="价格" prop="price">
          <el-input-number v-model="formData.price" :min="0" :precision="2" :step="0.1" style="width: 100%" />
        </el-form-item>
        <el-form-item label="分类" prop="category">
          <el-select v-model="formData.category" placeholder="请选择分类" style="width: 100%">
            <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
          </el-select>
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="formData.sort_order" :min="0" style="width: 100%" />
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

    <!-- 添加分类对话框 -->
    <el-dialog v-model="categoryDialogVisible" title="添加分类" width="400px">
      <el-form label-width="80px">
        <el-form-item label="分类名称">
          <el-input v-model="newCategory" placeholder="请输入分类名称，如：蔬菜、水果" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="categoryDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitCategory">确定</el-button>
      </template>
    </el-dialog>

    <!-- 添加商品公共属性对话框 -->
    <el-dialog v-model="attributeDialogVisible" title="添加商品公共属性" width="500px">
      <el-form label-width="100px">
        <el-form-item label="属性名称">
          <el-input v-model="newAttribute" placeholder="请输入属性名称，如：产地、规格、等级" />
        </el-form-item>
        <el-form-item>
          <el-alert
            title="提示"
            type="info"
            description="商品公共属性将应用于所有商品，可在编辑商品时填写具体值。"
            :closable="false"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="attributeDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitAttribute">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, FolderAdd, Setting } from '@element-plus/icons-vue'
import { getProducts, createProduct, updateProduct, deleteProduct, batchUpdateStatus, getDictOptions, addCategory, addAttribute } from '../../../api/desktop/products'

const loading = ref(false)
const productList = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const selectedIds = ref([])
const formRef = ref(null)

// 分类对话框
const categoryDialogVisible = ref(false)
const newCategory = ref('')

// 属性对话框
const attributeDialogVisible = ref(false)
const newAttribute = ref('')

const categories = ref([])
const units = ref([])

const searchForm = reactive({
  keyword: '',
  category: '',
  is_active: null
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const formData = reactive({
  id: null,
  product_name: '',
  product_code: '',
  shortcut_codes: [],
  unit: '',
  price: 0,
  category: '',
  sort_order: 0,
  is_active: true
})

const formRules = {
  product_name: [{ required: true, message: '请输入商品名称', trigger: 'blur' }],
  product_code: [{ required: true, message: '请输入商品编码', trigger: 'blur' }],
  unit: [{ required: true, message: '请输入单位', trigger: 'blur' }],
  price: [{ required: true, message: '请输入价格', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }]
}

// 加载商品列表
const loadProducts = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
      category: searchForm.category,
      is_active: searchForm.is_active
    }
    
    if (searchForm.keyword) {
      params.keyword = searchForm.keyword
    }

    const res = await getProducts(params)
    if (res.success) {
      productList.value = res.products || []
      pagination.total = res.count || 0
    }
  } catch (error) {
    ElMessage.error('加载商品失败')
  } finally {
    loading.value = false
  }
}

// 加载字典选项
const loadDictOptions = async () => {
  try {
    const res = await getDictOptions()
    if (res.success) {
      categories.value = res.options.categories || []
      units.value = res.options.units || []
    }
  } catch (error) {
    console.error('加载字典选项失败', error)
  }
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  loadProducts()
}

// 重置
const handleReset = () => {
  searchForm.keyword = ''
  searchForm.category = ''
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
const showEditDialog = (product) => {
  isEdit.value = true
  Object.assign(formData, {
    id: product.id,
    product_name: product.product_name,
    product_code: product.product_code,
    shortcut_codes: product.shortcut_codes || [],
    unit: product.unit,
    price: product.price,
    category: product.category,
    sort_order: product.sort_order || 0,
    is_active: product.is_active
  })
  dialogVisible.value = true
}

// 重置表单
const resetForm = () => {
  Object.assign(formData, {
    id: null,
    product_name: '',
    product_code: '',
    shortcut_codes: [],
    unit: '',
    price: 0,
    category: '',
    sort_order: 0,
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
        await updateProduct(formData.id, data)
        ElMessage.success('更新成功')
      } else {
        await createProduct(data)
        ElMessage.success('创建成功')
      }
      
      dialogVisible.value = false
      loadProducts()
    } catch (error) {
      ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
    } finally {
      submitting.value = false
    }
  })
}

// 删除商品
const handleDelete = (product) => {
  ElMessageBox.confirm(`确定要删除商品"${product.product_name}"吗?`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await deleteProduct(product.id)
      ElMessage.success('删除成功')
      loadProducts()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
}

// 选择变化
const handleSelectionChange = (selection) => {
  selectedIds.value = selection.map(item => item.id)
}

// 批量启用
const handleBatchEnable = async () => {
  try {
    await batchUpdateStatus(selectedIds.value, true)
    ElMessage.success('批量启用成功')
    loadProducts()
  } catch (error) {
    ElMessage.error('批量启用失败')
  }
}

// 批量禁用
const handleBatchDisable = async () => {
  try {
    await batchUpdateStatus(selectedIds.value, false)
    ElMessage.success('批量禁用成功')
    loadProducts()
  } catch (error) {
    ElMessage.error('批量禁用失败')
  }
}

// 显示添加分类对话框
const showCategoryDialog = () => {
  newCategory.value = ''
  categoryDialogVisible.value = true
}

// 提交新分类
const handleSubmitCategory = async () => {
  if (!newCategory.value.trim()) {
    ElMessage.warning('请输入分类名称')
    return
  }
  
  try {
    const res = await addCategory(newCategory.value.trim())
    if (res.success) {
      ElMessage.success('分类添加成功')
      categoryDialogVisible.value = false
      // 重新加载字典选项
      loadDictOptions()
    } else {
      ElMessage.error(res.error || '添加失败')
    }
  } catch (error) {
    ElMessage.error('添加分类失败')
  }
}

// 显示添加属性对话框
const showAttributeDialog = () => {
  newAttribute.value = ''
  attributeDialogVisible.value = true
}

// 提交新属性
const handleSubmitAttribute = async () => {
  if (!newAttribute.value.trim()) {
    ElMessage.warning('请输入属性名称')
    return
  }
  
  try {
    const res = await addAttribute(newAttribute.value.trim())
    if (res.success) {
      ElMessage.success('属性添加成功')
      attributeDialogVisible.value = false
      // 重新加载字典选项
      loadDictOptions()
    } else {
      ElMessage.error(res.error || '添加失败')
    }
  } catch (error) {
    ElMessage.error('添加属性失败')
  }
}

onMounted(() => {
  loadProducts()
  loadDictOptions()
})
</script>

<style scoped lang="scss">
.products-page {
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

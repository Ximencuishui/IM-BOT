<template>
  <div class="routes-page">
    <!-- 页面标题和操作栏 -->
    <div class="page-header">
      <h2 class="page-title">线路管理</h2>
      <div class="action-bar">
        <el-button type="primary" @click="showCreateDialog">
          <el-icon><Plus /></el-icon>
          新建线路
        </el-button>
        <el-button @click="loadRoutes">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <!-- 搜索和筛选 -->
    <el-card class="search-card" shadow="never">
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="线路名称">
          <el-input 
            v-model="searchForm.route_name" 
            placeholder="请输入线路名称" 
            clearable 
            style="width: 200px"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.is_active" placeholder="全部" clearable style="width: 120px">
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
    </el-card>

    <!-- 线路列表表格 -->
    <el-card class="table-card" shadow="never">
      <el-table 
        :data="routeList" 
        v-loading="loading"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="route_name" label="线路名称" min-width="150" />
        <el-table-column prop="route_code" label="线路编码" width="120" />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="product_count" label="商品数量" width="100" align="center">
          <template #default="{ row }">
            <el-tag type="info">{{ row.product_count || 0 }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="salesperson_name" label="负责销售" width="120" align="center">
          <template #default="{ row }">
            <span v-if="row.salesperson_name">{{ row.salesperson_name }}</span>
            <el-tag v-else type="warning" size="small">未分配</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_active === 1 ? 'success' : 'danger'">
              {{ row.is_active === 1 ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="showEditDialog(row)">
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <el-button size="small" type="primary" @click="showProductDialog(row)">
              <el-icon><Goods /></el-icon>
              商品
            </el-button>
            <el-button size="small" type="success" @click="showSalespersonDialog(row)">
              <el-icon><User /></el-icon>
              销售
            </el-button>
            <el-button 
              size="small" 
              type="danger" 
              @click="handleDelete(row)"
              :disabled="row.product_count > 0"
            >
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadRoutes"
          @current-change="loadRoutes"
        />
      </div>
    </el-card>

    <!-- 创建/编辑线路对话框 -->
    <el-dialog 
      v-model="dialogVisible" 
      :title="isEdit ? '编辑线路' : '新建线路'"
      width="600px"
      @close="resetForm"
    >
      <el-form 
        ref="formRef" 
        :model="formData" 
        :rules="formRules" 
        label-width="100px"
      >
        <el-form-item label="线路名称" prop="route_name">
          <el-input v-model="formData.route_name" placeholder="请输入线路名称" />
        </el-form-item>
        <el-form-item label="线路编码" prop="route_code">
          <el-input v-model="formData.route_code" placeholder="请输入线路编码(可选)" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input 
            v-model="formData.description" 
            type="textarea" 
            :rows="3"
            placeholder="请输入线路描述" 
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch 
            v-model="formData.is_active" 
            :active-value="1" 
            :inactive-value="0"
            active-text="启用" 
            inactive-text="禁用" 
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 线路商品管理对话框 -->
    <el-dialog 
      v-model="productDialogVisible" 
      :title="`管理商品 - ${currentRoute?.route_name || ''}`"
      width="900px"
      @close="resetProductForm"
    >
      <div class="product-management">
        <el-alert
          title="提示：可以为线路设置专属价格，不设置则使用商品基础价格"
          type="info"
          :closable="false"
          style="margin-bottom: 20px"
        />

        <!-- 已分配商品列表 -->
        <div class="assigned-products">
          <h4>已分配商品</h4>
          <el-table 
            :data="assignedProducts" 
            v-loading="productLoading"
            border
            style="width: 100%; margin-bottom: 20px"
          >
            <el-table-column prop="sort_order" label="序号" width="80" align="center" />
            <el-table-column prop="product_name" label="商品名称" min-width="150" />
            <el-table-column prop="unit" label="单位" width="80" align="center" />
            <el-table-column label="价格(元)" width="150">
              <template #default="{ row }">
                <el-input-number 
                  v-model="row.custom_price" 
                  :min="0" 
                  :precision="2" 
                  :step="0.1"
                  size="small"
                  placeholder="使用基础价"
                  controls-position="right"
                  style="width: 100%"
                  @change="handlePriceChange(row)"
                />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150" align="center">
              <template #default="{ row, $index }">
                <el-button 
                  size="small" 
                  @click="moveProductUp($index)"
                  :disabled="$index === 0"
                >
                  上移
                </el-button>
                <el-button 
                  size="small" 
                  @click="moveProductDown($index)"
                  :disabled="$index === assignedProducts.length - 1"
                >
                  下移
                </el-button>
                <el-button 
                  size="small" 
                  type="danger" 
                  @click="removeProduct(row)"
                >
                  移除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 添加商品 -->
        <div class="add-products">
          <h4>添加商品</h4>
          <el-transfer
            v-model="selectedProductIds"
            :data="availableProducts"
            :titles="['可选商品', '已选商品']"
            :props="{ key: 'id', label: 'product_name' }"
            filterable
            filter-placeholder="搜索商品"
            style="text-align: left; display: inline-block"
          />
          <div style="margin-top: 20px">
            <el-button type="primary" @click="handleAssignProducts" :loading="assigning">
              确认添加
            </el-button>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="productDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 销售人员分配对话框 -->
    <el-dialog 
      v-model="salespersonDialogVisible" 
      :title="`分配销售人员 - ${currentRoute?.route_name || ''}`"
      width="600px"
      @close="resetSalespersonForm"
    >
      <div class="salesperson-management">
        <el-alert
          title="提示：为线路分配负责的销售人员"
          type="info"
          :closable="false"
          style="margin-bottom: 20px"
        />

        <el-form 
          ref="salespersonFormRef" 
          :model="salespersonFormData" 
          label-width="100px"
        >
          <el-form-item label="当前销售">
            <el-input 
              v-model="currentSalespersonName" 
              disabled 
              placeholder="未分配"
            />
          </el-form-item>
          <el-form-item label="选择销售" prop="salesperson_id">
            <el-select 
              v-model="salespersonFormData.salesperson_id" 
              placeholder="请选择销售人员" 
              clearable
              style="width: 100%"
            >
              <el-option
                v-for="sp in availableSalespersons"
                :key="sp.id"
                :label="`${sp.name} (${sp.phone || '无电话'})`"
                :value="sp.id"
              />
            </el-select>
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <el-button @click="salespersonDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAssignSalesperson" :loading="assigningSalesperson">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Search, Edit, Delete, Goods, User } from '@element-plus/icons-vue'
import { 
  getRoutes, 
  createRoute, 
  updateRoute, 
  deleteRoute,
  getRouteProducts,
  assignProductsToRoute,
  updateRouteProductSort,
  removeProductFromRoute,
  updateRouteProductPrice
} from '../../../api/desktop/routes'
import { getProducts } from '../../../api/desktop/products'
import { getSalespersons, updateSalesperson } from '../../../api/desktop/salespersons'

// 数据定义
const loading = ref(false)
const routeList = ref([])
const searchForm = reactive({
  route_name: '',
  is_active: null
})
const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

// 对话框相关
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref(null)
const formData = reactive({
  id: null,
  route_name: '',
  route_code: '',
  description: '',
  is_active: 1
})

// 表单验证规则
const formRules = {
  route_name: [
    { required: true, message: '请输入线路名称', trigger: 'blur' }
  ]
}

// 商品管理相关
const productDialogVisible = ref(false)
const currentRoute = ref(null)
const productLoading = ref(false)
const assignedProducts = ref([])
const availableProducts = ref([])
const selectedProductIds = ref([])
const assigning = ref(false)

// 销售人员管理相关
const salespersonDialogVisible = ref(false)
const salespersonFormRef = ref(null)
const salespersonFormData = reactive({
  salesperson_id: null
})
const availableSalespersons = ref([])
const assigningSalesperson = ref(false)
const currentSalespersonName = ref('')

// 加载线路列表
const loadRoutes = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      per_page: pagination.pageSize,
      ...searchForm
    }
    
    // 过滤空值
    Object.keys(params).forEach(key => {
      if (params[key] === '' || params[key] === null || params[key] === undefined) {
        delete params[key]
      }
    })

    const res = await getRoutes(params)
    if (res.success) {
      routeList.value = res.routes || []
      pagination.total = res.count || 0
      
      // 获取每个线路的销售人员信息
      await loadSalespersonInfoForRoutes()
    } else {
      ElMessage.error(res.error || '加载线路列表失败')
    }
  } catch (error) {
    console.error('加载线路列表失败:', error)
    ElMessage.error('加载线路列表失败')
  } finally {
    loading.value = false
  }
}

// 为线路加载销售人员信息
const loadSalespersonInfoForRoutes = async () => {
  try {
    // 获取所有销售人员
    const spRes = await getSalespersons({ is_active: 'true' })
    if (spRes.success) {
      const salespersons = spRes.salespersons || []
      
      // 为每个线路设置销售人员名称
      routeList.value.forEach(route => {
        const salesperson = salespersons.find(sp => sp.route_id === route.id)
        route.salesperson_name = salesperson ? salesperson.name : null
        route.salesperson_id = salesperson ? salesperson.id : null
      })
    }
  } catch (error) {
    console.error('加载销售人员信息失败:', error)
  }
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  loadRoutes()
}

// 重置搜索
const handleReset = () => {
  searchForm.route_name = ''
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
const showEditDialog = (route) => {
  isEdit.value = true
  Object.assign(formData, {
    id: route.id,
    route_name: route.route_name,
    route_code: route.route_code || '',
    description: route.description || '',
    is_active: route.is_active
  })
  dialogVisible.value = true
}

// 重置表单
const resetForm = () => {
  Object.assign(formData, {
    id: null,
    route_name: '',
    route_code: '',
    description: '',
    is_active: 1
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
      let res
      if (isEdit.value) {
        res = await updateRoute(formData.id, formData)
      } else {
        res = await createRoute(formData)
      }

      if (res.success) {
        ElMessage.success(isEdit.value ? '更新成功' : '创建成功')
        dialogVisible.value = false
        loadRoutes()
      } else {
        ElMessage.error(res.error || '操作失败')
      }
    } catch (error) {
      console.error('提交失败:', error)
      ElMessage.error('操作失败')
    } finally {
      submitting.value = false
    }
  })
}

// 删除线路
const handleDelete = (route) => {
  ElMessageBox.confirm(
    `确定要删除线路"${route.route_name}"吗？`,
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      const res = await deleteRoute(route.id)
      if (res.success) {
        ElMessage.success('删除成功')
        loadRoutes()
      } else {
        ElMessage.error(res.error || '删除失败')
      }
    } catch (error) {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }).catch(() => {
    // 用户取消
  })
}

// 显示商品管理对话框
const showProductDialog = async (route) => {
  currentRoute.value = route
  productDialogVisible.value = true
  await loadAssignedProducts()
  await loadAvailableProducts()
}

// 加载已分配商品
const loadAssignedProducts = async () => {
  if (!currentRoute.value) return
  
  productLoading.value = true
  try {
    const res = await getRouteProducts(currentRoute.value.id)
    if (res.success) {
      assignedProducts.value = res.products || []
    }
  } catch (error) {
    console.error('加载已分配商品失败:', error)
    ElMessage.error('加载已分配商品失败')
  } finally {
    productLoading.value = false
  }
}

// 加载可用商品
const loadAvailableProducts = async () => {
  try {
    const res = await getProducts({ page: 1, per_page: 1000, is_active: 1 })
    if (res.success) {
      // 过滤掉已经分配的商品
      const assignedIds = new Set(assignedProducts.value.map(p => p.product_id))
      availableProducts.value = (res.products || []).filter(p => !assignedIds.has(p.id))
    }
  } catch (error) {
    console.error('加载可用商品失败:', error)
  }
}

// 处理价格变化
const handlePriceChange = async (product) => {
  if (!currentRoute.value) return
  
  try {
    const res = await updateRouteProductPrice(
      currentRoute.value.id,
      product.product_id,
      product.custom_price
    )
    
    if (res.success) {
      ElMessage.success('价格更新成功')
    } else {
      ElMessage.error(res.error || '价格更新失败')
    }
  } catch (error) {
    console.error('更新价格失败:', error)
    ElMessage.error('价格更新失败')
  }
}

// 上移商品
const moveProductUp = async (index) => {
  if (index === 0) return
  
  const product = assignedProducts.value[index]
  const prevProduct = assignedProducts.value[index - 1]
  
  // 交换排序号
  const tempSort = product.sort_order
  product.sort_order = prevProduct.sort_order
  prevProduct.sort_order = tempSort
  
  // 重新排序数组
  assignedProducts.value.sort((a, b) => a.sort_order - b.sort_order)
  
  // 更新到服务器
  try {
    await updateRouteProductSort(
      currentRoute.value.id,
      product.product_id,
      product.sort_order
    )
    await updateRouteProductSort(
      currentRoute.value.id,
      prevProduct.product_id,
      prevProduct.sort_order
    )
    ElMessage.success('排序更新成功')
  } catch (error) {
    console.error('更新排序失败:', error)
    ElMessage.error('更新排序失败')
    // 恢复原来的顺序
    const tempSort = product.sort_order
    product.sort_order = prevProduct.sort_order
    prevProduct.sort_order = tempSort
    assignedProducts.value.sort((a, b) => a.sort_order - b.sort_order)
  }
}

// 下移商品
const moveProductDown = async (index) => {
  if (index === assignedProducts.value.length - 1) return
  
  const product = assignedProducts.value[index]
  const nextProduct = assignedProducts.value[index + 1]
  
  // 交换排序号
  const tempSort = product.sort_order
  product.sort_order = nextProduct.sort_order
  nextProduct.sort_order = tempSort
  
  // 重新排序数组
  assignedProducts.value.sort((a, b) => a.sort_order - b.sort_order)
  
  // 更新到服务器
  try {
    await updateRouteProductSort(
      currentRoute.value.id,
      product.product_id,
      product.sort_order
    )
    await updateRouteProductSort(
      currentRoute.value.id,
      nextProduct.product_id,
      nextProduct.sort_order
    )
    ElMessage.success('排序更新成功')
  } catch (error) {
    console.error('更新排序失败:', error)
    ElMessage.error('更新排序失败')
    // 恢复原来的顺序
    const tempSort = product.sort_order
    product.sort_order = nextProduct.sort_order
    nextProduct.sort_order = tempSort
    assignedProducts.value.sort((a, b) => a.sort_order - b.sort_order)
  }
}

// 移除商品
const removeProduct = (product) => {
  ElMessageBox.confirm(
    `确定要从线路中移除商品"${product.product_name}"吗？`,
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      const res = await removeProductFromRoute(
        currentRoute.value.id,
        product.product_id
      )
      
      if (res.success) {
        ElMessage.success('移除成功')
        await loadAssignedProducts()
        await loadAvailableProducts()
      } else {
        ElMessage.error(res.error || '移除失败')
      }
    } catch (error) {
      console.error('移除商品失败:', error)
      ElMessage.error('移除商品失败')
    }
  }).catch(() => {
    // 用户取消
  })
}

// 分配商品到线路
const handleAssignProducts = async () => {
  if (selectedProductIds.value.length === 0) {
    ElMessage.warning('请选择要添加的商品')
    return
  }

  assigning.value = true
  try {
    const res = await assignProductsToRoute(
      currentRoute.value.id,
      selectedProductIds.value
    )
    
    if (res.success) {
      ElMessage.success(`成功添加${res.assigned_count}个商品`)
      selectedProductIds.value = []
      await loadAssignedProducts()
      await loadAvailableProducts()
    } else {
      ElMessage.error(res.error || '添加商品失败')
    }
  } catch (error) {
    console.error('添加商品失败:', error)
    ElMessage.error('添加商品失败')
  } finally {
    assigning.value = false
  }
}

// 重置商品表单
const resetProductForm = () => {
  selectedProductIds.value = []
  currentRoute.value = null
  assignedProducts.value = []
  availableProducts.value = []
}

// 显示销售人员分配对话框
const showSalespersonDialog = async (route) => {
  currentRoute.value = route
  salespersonDialogVisible.value = true
  
  // 设置当前销售人员名称
  currentSalespersonName.value = route.salesperson_name || ''
  salespersonFormData.salesperson_id = route.salesperson_id || null
  
  // 加载可用销售人员
  await loadAvailableSalespersons()
}

// 加载可用销售人员
const loadAvailableSalespersons = async () => {
  try {
    const res = await getSalespersons({ is_active: 'true' })
    if (res.success) {
      availableSalespersons.value = res.salespersons || []
    }
  } catch (error) {
    console.error('加载销售人员失败:', error)
    ElMessage.error('加载销售人员失败')
  }
}

// 分配销售人员
const handleAssignSalesperson = async () => {
  if (!currentRoute.value) return
  
  assigningSalesperson.value = true
  try {
    // 如果有之前分配的销售人员，先清除其线路ID
    if (currentRoute.value.salesperson_id) {
      await updateSalesperson(currentRoute.value.salesperson_id, {
        route_id: null
      })
    }
    
    // 如果选择了新的销售人员，则分配线路
    if (salespersonFormData.salesperson_id) {
      await updateSalesperson(salespersonFormData.salesperson_id, {
        route_id: currentRoute.value.id
      })
    }
    
    ElMessage.success('销售人员分配成功')
    salespersonDialogVisible.value = false
    
    // 重新加载线路列表以更新显示
    await loadRoutes()
  } catch (error) {
    console.error('分配销售人员失败:', error)
    ElMessage.error('分配销售人员失败')
  } finally {
    assigningSalesperson.value = false
  }
}

// 重置销售人员表单
const resetSalespersonForm = () => {
  salespersonFormData.salesperson_id = null
  currentSalespersonName.value = ''
  currentRoute.value = null
  availableSalespersons.value = []
}

// 初始化
onMounted(() => {
  loadRoutes()
})
</script>

<style scoped lang="scss">
.routes-page {
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;

    .page-title {
      font-size: 24px;
      font-weight: 600;
      color: #1e293b;
      margin: 0;
    }

    .action-bar {
      display: flex;
      gap: 10px;
    }
  }

  .search-card {
    margin-bottom: 20px;

    .search-form {
      margin-bottom: 0;
    }
  }

  .table-card {
    .pagination-container {
      margin-top: 20px;
      display: flex;
      justify-content: flex-end;
    }
  }

  .product-management {
    .assigned-products,
    .add-products {
      h4 {
        margin: 0 0 15px 0;
        font-size: 16px;
        color: #1e293b;
      }
    }

    .add-products {
      margin-top: 30px;
      padding-top: 30px;
      border-top: 1px solid #e2e8f0;
    }
  }

  .salesperson-management {
    .form-tip {
      font-size: 12px;
      color: #94a3b8;
      margin-top: 5px;
    }
  }
}
</style>

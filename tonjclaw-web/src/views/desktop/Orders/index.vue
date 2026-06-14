<template>
  <div class="orders-page">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-cards">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-icon" style="background-color: #3b82f6">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ todayStats.orderCount || 0 }}</div>
              <div class="stat-label">今日订单</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-icon" style="background-color: #10b981">
              <el-icon><Check /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ todayStats.completedCount || 0 }}</div>
              <div class="stat-label">已完成</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-icon" style="background-color: #f59e0b">
              <el-icon><Clock /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ todayStats.pendingCount || 0 }}</div>
              <div class="stat-label">待处理</div>
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
              <div class="stat-value">¥{{ todayStats.totalAmount || 0 }}</div>
              <div class="stat-label">今日销售额</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 搜索和操作栏 -->
    <el-card class="search-card">
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="客户">
          <el-input v-model="searchForm.customer" placeholder="输入客户名称" clearable />
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="searchForm.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="全部" clearable>
            <el-option label="待处理" value="pending" />
            <el-option label="已完成" value="completed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="销售员">
          <el-select v-model="searchForm.salesperson_id" placeholder="全部" clearable>
            <el-option
              v-for="sp in salespersonList"
              :key="sp.id"
              :label="sp.name"
              :value="sp.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="线路">
          <el-select v-model="searchForm.route_id" placeholder="全部" clearable>
            <el-option
              v-for="route in routeList"
              :key="route.id"
              :label="route.route_name"
              :value="route.id"
            />
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
        <el-button type="success" @click="showParseDialog = true">
          <el-icon><ChatDotRound /></el-icon>
          解析消息
        </el-button>
        <el-button 
          type="primary" 
          @click="handleBatchConfirm" 
          :disabled="selectedOrders.length === 0"
        >
          批量确认
        </el-button>
        <el-button type="warning" @click="handleExport">
          <el-icon><Download /></el-icon>
          导出Excel
        </el-button>
      </div>
    </el-card>

    <!-- 订单表格 -->
    <el-card class="table-card">
      <el-table
        v-loading="loading"
        :data="orderList"
        border
        stripe
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="order_no" label="订单号" width="120" />
        <el-table-column prop="customer_name" label="客户" width="120" />
        <el-table-column label="商品明细" min-width="200">
          <template #default="{ row }">
            <div v-for="(item, index) in row.items" :key="index" class="order-item">
              {{ item.product_name }} x {{ item.quantity }}{{ item.unit }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="total_amount" label="金额" width="100">
          <template #default="{ row }">
            ¥{{ row.total_amount }}
          </template>
        </el-table-column>
        <el-table-column prop="order_date" label="日期" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="viewDetail(row)">
              详情
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
          @size-change="loadOrders"
          @current-change="loadOrders"
        />
      </div>
    </el-card>

    <!-- 订单详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="订单详情" width="600px">
      <div v-if="currentOrder" class="order-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="订单号">{{ currentOrder.order_no }}</el-descriptions-item>
          <el-descriptions-item label="客户">{{ currentOrder.customer_name }}</el-descriptions-item>
          <el-descriptions-item label="日期">{{ currentOrder.order_date }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(currentOrder.status)">
              {{ getStatusText(currentOrder.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="总金额" :span="2">
            ¥{{ currentOrder.total_amount }}
          </el-descriptions-item>
          <el-descriptions-item label="备注" :span="2">
            {{ currentOrder.remark || '无' }}
          </el-descriptions-item>
        </el-descriptions>

        <h4 style="margin-top: 20px">商品明细</h4>
        <el-table :data="currentOrder.items" border>
          <el-table-column prop="product_name" label="商品名称" />
          <el-table-column prop="quantity" label="数量" width="100" />
          <el-table-column prop="unit" label="单位" width="80" />
          <el-table-column prop="price" label="单价" width="100">
            <template #default="{ row }">¥{{ row.price }}</template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>

    <!-- 消息解析对话框 -->
    <el-dialog v-model="showParseDialog" title="解析订单消息" width="700px">
      <el-form :model="parseForm" label-width="100px">
        <el-form-item label="消息内容">
          <el-input
            v-model="parseForm.content"
            type="textarea"
            :rows="6"
            placeholder="请输入微信消息内容，例如：来10斤土豆，要嫩的"
          />
        </el-form-item>
        <el-form-item label="群ID">
          <el-input v-model="parseForm.group_id" placeholder="可选，用于识别客户" />
        </el-form-item>
        <el-form-item label="发送人">
          <el-input v-model="parseForm.sender" placeholder="可选，用于识别客户" />
        </el-form-item>
        <el-form-item label="自动添加">
          <el-checkbox v-model="parseForm.autoAddRule">
            自动添加到解析规则表
          </el-checkbox>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showParseDialog = false">取消</el-button>
        <el-button type="primary" @click="handleParseOrder" :loading="parsing">
          解析并创建
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getOrders, parseOrder, deleteOrder, batchConfirmOrders } from '../../../api/desktop/orders'
import { exportReport } from '../../../api/desktop/reports'
import { getSalespersons } from '../../../api/desktop/salespersons'
import { getRoutes } from '../../../api/desktop/customers'

const loading = ref(false)
const orderList = ref([])
const showParseDialog = ref(false)
const detailDialogVisible = ref(false)
const currentOrder = ref(null)
const parsing = ref(false)
const selectedOrders = ref([])

const todayStats = ref({
  orderCount: 0,
  completedCount: 0,
  pendingCount: 0,
  totalAmount: 0
})

const searchForm = reactive({
  customer: '',
  dateRange: [],
  status: '',
  salesperson_id: null,
  route_id: null
})

const salespersonList = ref([])
const routeList = ref([])

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const parseForm = reactive({
  content: '',
  group_id: '',
  sender: '',
  autoAddRule: false
})

// 加载订单列表
const loadOrders = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
      customer: searchForm.customer,
      status: searchForm.status
    }
    
    if (searchForm.dateRange && searchForm.dateRange.length === 2) {
      params.start_date = searchForm.dateRange[0]
      params.end_date = searchForm.dateRange[1]
    }

    const res = await getOrders(params)
    if (res.success) {
      orderList.value = res.orders || []
      pagination.total = res.total || 0
    }
  } catch (error) {
    ElMessage.error('加载订单失败')
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  loadOrders()
}

// 重置
const handleReset = () => {
  searchForm.customer = ''
  searchForm.dateRange = []
  searchForm.status = ''
  handleSearch()
}

// 查看详情
const viewDetail = (order) => {
  currentOrder.value = order
  detailDialogVisible.value = true
}

// 删除订单
const handleDelete = (order) => {
  ElMessageBox.confirm('确定要删除该订单吗?', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await deleteOrder(order.id)
      ElMessage.success('删除成功')
      loadOrders()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
}

// 解析订单
const handleParseOrder = async () => {
  if (!parseForm.content) {
    ElMessage.warning('请输入消息内容')
    return
  }

  parsing.value = true
  try {
    const res = await parseOrder(parseForm)
    if (res.success) {
      ElMessage.success('订单创建成功' + (parseForm.autoAddRule ? '，解析规则已自动添加' : ''))
      showParseDialog.value = false
      parseForm.content = ''
      parseForm.group_id = ''
      parseForm.sender = ''
      parseForm.autoAddRule = false
      loadOrders()
    } else {
      ElMessage.error(res.error || '解析失败')
    }
  } catch (error) {
    ElMessage.error('解析失败')
  } finally {
    parsing.value = false
  }
}

// 导出Excel
const handleExport = async () => {
  try {
    const params = {}
    if (searchForm.dateRange && searchForm.dateRange.length === 2) {
      params.date = searchForm.dateRange[0]
    }
    
    const res = await exportReport(params)
    const blob = new Blob([res], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `订单报表_${new Date().toISOString().split('T')[0]}.xlsx`
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

// 选择变化
const handleSelectionChange = (selection) => {
  selectedOrders.value = selection
}

// 获取状态类型
const getStatusType = (status) => {
  const map = {
    pending: 'warning',
    completed: 'success',
    cancelled: 'danger'
  }
  return map[status] || 'info'
}

// 获取状态文本
const getStatusText = (status) => {
  const map = {
    pending: '待处理',
    completed: '已完成',
    cancelled: '已取消'
  }
  return map[status] || status
}

// 批量确认订单
const handleBatchConfirm = async () => {
  if (selectedOrders.value.length === 0) return
  
  try {
    await ElMessageBox.confirm(`确定要确认选中的 ${selectedOrders.value.length} 个订单吗?`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    const ids = selectedOrders.value.map(o => o.id)
    await batchConfirmOrders(ids)
    ElMessage.success('批量确认成功')
    loadOrders()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('批量确认失败')
    }
  }
}

// 加载辅助数据（销售员和线路）
const loadAuxData = async () => {
  try {
    const [spRes, routeRes] = await Promise.all([
      getSalespersons({ is_active: 'true' }),
      getRoutes()
    ])
    if (spRes.success) salespersonList.value = spRes.salespersons || []
    if (routeRes.success) routeList.value = routeRes.routes || []
  } catch (error) {
    console.error('加载辅助数据失败', error)
  }
}

onMounted(() => {
  loadOrders()
  loadAuxData()
})
</script>

<style scoped lang="scss">
.orders-page {
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
    .order-item {
      padding: 2px 0;
      font-size: 13px;
    }
    
    .pagination {
      margin-top: 20px;
      display: flex;
      justify-content: flex-end;
    }
  }

  .order-detail {
    h4 {
      color: #1e293b;
      font-size: 16px;
    }
  }
}
</style>

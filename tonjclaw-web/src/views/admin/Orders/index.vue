<template>
  <div class="orders-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>订单与续费管理</h2>
    </div>

    <el-tabs v-model="activeTab" type="border-card">
      <!-- 订单管理 -->
      <el-tab-pane label="订单管理" name="orders">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>订单列表</span>
              <el-input
                v-model="orderSearchKeyword"
                placeholder="搜索订单号或客户"
                style="width: 300px"
                clearable
                @clear="loadOrders"
                @keyup.enter="loadOrders"
              >
                <template #append>
                  <el-button @click="loadOrders">
                    <el-icon><Search /></el-icon>
                  </el-button>
                </template>
              </el-input>
            </div>
          </template>

          <el-table :data="orders" v-loading="ordersLoading" stripe>
            <el-table-column prop="id" label="订单ID" width="80" />
            <el-table-column prop="order_no" label="订单号" width="180" />
            <el-table-column prop="customer_name" label="客户" width="120" />
            <el-table-column label="订单金额" width="120">
              <template #default="{ row }">
                ¥{{ row.total_amount?.toFixed(2) || '0.00' }}
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">
                  {{ getStatusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="170">
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="viewOrderDetail(row)">详情</el-button>
                <el-button 
                  v-if="row.status === 'pending'" 
                  link 
                  type="success" 
                  size="small" 
                  @click="confirmOrder(row)"
                >
                  确认
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-model:current-page="orderPage"
            v-model:page-size="orderPageSize"
            :total="orderTotal"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @size-change="loadOrders"
            @current-change="loadOrders"
            style="margin-top: 20px; justify-content: flex-end"
          />
        </el-card>
      </el-tab-pane>

      <!-- 续费历史 -->
      <el-tab-pane label="续费历史" name="renewals">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>续费记录</span>
              <el-button @click="loadRenewalStats">
                <el-icon><Refresh /></el-icon> 刷新统计
              </el-button>
            </div>
          </template>

          <!-- 统计卡片 -->
          <el-row :gutter="20" style="margin-bottom: 20px;">
            <el-col :span="6">
              <el-statistic title="本月续费次数" :value="renewalStats.monthly_count || 0" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="本月续费金额" :value="renewalStats.monthly_amount || 0" prefix="¥" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="总续费次数" :value="renewalStats.total_count || 0" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="总续费金额" :value="renewalStats.total_amount || 0" prefix="¥" />
            </el-col>
          </el-row>

          <el-table :data="renewalHistory" v-loading="renewalsLoading" stripe>
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="license_code" label="授权码" width="180" />
            <el-table-column prop="customer_name" label="客户" width="120" />
            <el-table-column label="续费时长" width="100">
              <template #default="{ row }">
                {{ row.extend_months }} 个月
              </template>
            </el-table-column>
            <el-table-column label="续费金额" width="120">
              <template #default="{ row }">
                ¥{{ row.amount?.toFixed(2) || '0.00' }}
              </template>
            </el-table-column>
            <el-table-column prop="renewal_type" label="续费类型" width="100">
              <template #default="{ row }">
                <el-tag size="small">{{ getRenewalTypeLabel(row.renewal_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="operator" label="操作人" width="100" />
            <el-table-column prop="created_at" label="续费时间" width="170">
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column prop="remark" label="备注" min-width="150" show-overflow-tooltip />
          </el-table>

          <el-pagination
            v-model:current-page="renewalPage"
            v-model:page-size="renewalPageSize"
            :total="renewalTotal"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @size-change="loadRenewalHistory"
            @current-change="loadRenewalHistory"
            style="margin-top: 20px; justify-content: flex-end"
          />
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 订单详情对话框 -->
    <el-dialog v-model="showOrderDetailDialog" title="订单详情" width="800px">
      <el-descriptions :column="2" border v-if="currentOrder">
        <el-descriptions-item label="订单号">{{ currentOrder.order_no }}</el-descriptions-item>
        <el-descriptions-item label="客户">{{ currentOrder.customer_name }}</el-descriptions-item>
        <el-descriptions-item label="订单金额">¥{{ currentOrder.total_amount?.toFixed(2) }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(currentOrder.status)">
            {{ getStatusLabel(currentOrder.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间" :span="2">{{ formatDate(currentOrder.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ currentOrder.remark || '无' }}</el-descriptions-item>
      </el-descriptions>

      <div v-if="currentOrder?.items?.length" style="margin-top: 20px;">
        <h4>订单明细：</h4>
        <el-table :data="currentOrder.items" border size="small">
          <el-table-column prop="product_name" label="商品名称" />
          <el-table-column prop="quantity" label="数量" width="80" />
          <el-table-column prop="unit_price" label="单价" width="100">
            <template #default="{ row }">
              ¥{{ row.unit_price?.toFixed(2) }}
            </template>
          </el-table-column>
          <el-table-column prop="subtotal" label="小计" width="100">
            <template #default="{ row }">
              ¥{{ row.subtotal?.toFixed(2) }}
            </template>
          </el-table-column>
        </el-table>
      </div>

      <template #footer>
        <el-button @click="showOrderDetailDialog = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh } from '@element-plus/icons-vue'
import {
  getOrders,
  getOrderDetail,
  updateOrderStatus,
  getRenewalHistory,
  getRenewalStats
} from '@/api/admin/orders'
import dayjs from 'dayjs'

// 标签页
const activeTab = ref('orders')

// 订单管理
const orders = ref([])
const ordersLoading = ref(false)
const orderSearchKeyword = ref('')
const orderPage = ref(1)
const orderPageSize = ref(20)
const orderTotal = ref(0)

// 续费历史
const renewalHistory = ref([])
const renewalsLoading = ref(false)
const renewalPage = ref(1)
const renewalPageSize = ref(20)
const renewalTotal = ref(0)
const renewalStats = reactive({
  monthly_count: 0,
  monthly_amount: 0,
  total_count: 0,
  total_amount: 0
})

// 订单详情
const showOrderDetailDialog = ref(false)
const currentOrder = ref(null)

// 加载订单列表
const loadOrders = async () => {
  ordersLoading.value = true
  try {
    const res = await getOrders({
      page: orderPage.value,
      per_page: orderPageSize.value,
      keyword: orderSearchKeyword.value
    })
    
    if (res.success) {
      orders.value = res.orders || []
      orderTotal.value = res.total || 0
    } else {
      ElMessage.error(res.message || '加载失败')
    }
  } catch (error) {
    ElMessage.error('加载失败：' + error.message)
  } finally {
    ordersLoading.value = false
  }
}

// 查看订单详情
const viewOrderDetail = async (order) => {
  try {
    const res = await getOrderDetail(order.id)
    if (res.success) {
      currentOrder.value = res.order
      showOrderDetailDialog.value = true
    } else {
      ElMessage.error(res.message || '加载失败')
    }
  } catch (error) {
    ElMessage.error('加载失败：' + error.message)
  }
}

// 确认订单
const confirmOrder = async (order) => {
  try {
    await ElMessageBox.confirm('确定要确认这个订单吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    const res = await updateOrderStatus(order.id, { status: 'confirmed' })
    if (res.success) {
      ElMessage.success('订单已确认')
      loadOrders()
    } else {
      ElMessage.error(res.message || '操作失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败：' + error.message)
    }
  }
}

// 加载续费历史
const loadRenewalHistory = async () => {
  renewalsLoading.value = true
  try {
    const res = await getRenewalHistory({
      page: renewalPage.value,
      per_page: renewalPageSize.value
    })
    
    if (res.success) {
      renewalHistory.value = res.history || []
      renewalTotal.value = res.total || 0
    } else {
      ElMessage.error(res.message || '加载失败')
    }
  } catch (error) {
    ElMessage.error('加载失败：' + error.message)
  } finally {
    renewalsLoading.value = false
  }
}

// 加载续费统计
const loadRenewalStats = async () => {
  try {
    const res = await getRenewalStats()
    if (res.success) {
      Object.assign(renewalStats, res.stats)
    }
  } catch (error) {
    console.error('加载统计失败:', error)
  }
}

// 获取状态类型
const getStatusType = (status) => {
  const types = {
    pending: 'warning',
    confirmed: 'success',
    cancelled: 'danger',
    completed: 'info'
  }
  return types[status] || ''
}

// 获取状态标签
const getStatusLabel = (status) => {
  const labels = {
    pending: '待确认',
    confirmed: '已确认',
    cancelled: '已取消',
    completed: '已完成'
  }
  return labels[status] || status
}

// 获取续费类型标签
const getRenewalTypeLabel = (type) => {
  const labels = {
    manual: '手动续费',
    auto: '自动续费',
    admin: '管理员展期'
  }
  return labels[type] || type
}

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return dayjs(dateStr).format('YYYY-MM-DD HH:mm:ss')
}

onMounted(() => {
  loadOrders()
  loadRenewalHistory()
  loadRenewalStats()
})
</script>

<style scoped>
.orders-container {
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

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>

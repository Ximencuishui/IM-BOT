<template>
  <div class="dashboard-page">
    <!-- 顶部操作栏 -->
    <div class="action-bar">
      <el-button type="primary" @click="refreshAllData" :loading="refreshing">
        <el-icon><Refresh /></el-icon>
        刷新数据
      </el-button>
      <el-button @click="exportDashboard">
        <el-icon><Download /></el-icon>
        导出报表
      </el-button>
      <el-date-picker
        v-model="quickDate"
        type="date"
        placeholder="快速选择日期"
        size="default"
        value-format="YYYY-MM-DD"
        @change="handleDateChange"
      />
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-cards">
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-item">
            <div class="stat-icon" style="background: linear-gradient(135deg, #5b4ae8 0%, #8b5cf6 100%)">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ dashboardStats.totalOrders || 0 }}</div>
              <div class="stat-label">今日订单</div>
              <div class="stat-trend" v-if="dashboardStats.orderGrowth !== undefined">
                <span :class="dashboardStats.orderGrowth >= 0 ? 'trend-up' : 'trend-down'">
                  {{ dashboardStats.orderGrowth >= 0 ? '↑' : '↓' }} {{ Math.abs(dashboardStats.orderGrowth) }}%
                </span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-item">
            <div class="stat-icon" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%)">
              <el-icon><Coin /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">¥{{ formatAmount(dashboardStats.totalAmount) }}</div>
              <div class="stat-label">今日销售额</div>
              <div class="stat-trend" v-if="dashboardStats.amountGrowth !== undefined">
                <span :class="dashboardStats.amountGrowth >= 0 ? 'trend-up' : 'trend-down'">
                  {{ dashboardStats.amountGrowth >= 0 ? '↑' : '↓' }} {{ Math.abs(dashboardStats.amountGrowth) }}%
                </span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-item">
            <div class="stat-icon" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)">
              <el-icon><User /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ dashboardStats.activeCustomers || 0 }}</div>
              <div class="stat-label">活跃客户</div>
              <div class="stat-sub">总客户数 {{ dashboardStats.customersCount || 0 }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :sm="12" :md="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-item">
            <div class="stat-icon" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)">
              <el-icon><Goods /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ dashboardStats.productsCount || 0 }}</div>
              <div class="stat-label">商品种类</div>
              <div class="stat-sub">热销商品 {{ dashboardStats.hotProducts || 0 }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 - 第一行 -->
    <el-row :gutter="20" class="charts-section">
      <!-- 销售趋势图 -->
      <el-col :xs="24" :lg="16">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">📈 销售趋势</span>
              <el-radio-group v-model="trendDays" size="small" @change="loadSalesTrend">
                <el-radio-button :label="7">近7天</el-radio-button>
                <el-radio-button :label="14">近14天</el-radio-button>
                <el-radio-button :label="30">近30天</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div ref="salesTrendChartRef" class="chart-container" style="height: 350px"></div>
        </el-card>
      </el-col>

      <!-- 订单状态分布 -->
      <el-col :xs="24" :lg="8">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">📊 订单状态</span>
            </div>
          </template>
          <div ref="orderStatusChartRef" class="chart-container" style="height: 350px"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 - 第二行 -->
    <el-row :gutter="20" class="charts-section">
      <!-- 商品销量排行 -->
      <el-col :xs="24" :lg="12">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">🏆 商品销量排行</span>
              <el-select v-model="rankingPeriod" size="small" @change="loadProductRanking">
                <el-option label="本周" value="week" />
                <el-option label="本月" value="month" />
              </el-select>
            </div>
          </template>
          <div ref="productRankingChartRef" class="chart-container" style="height: 350px"></div>
        </el-card>
      </el-col>

      <!-- 客户分布 -->
      <el-col :xs="24" :lg="12">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">👥 客户分布</span>
            </div>
          </template>
          <div ref="customerDistChartRef" class="chart-container" style="height: 350px"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 热销品类和近期订单 -->
    <el-row :gutter="20" class="charts-section">
      <!-- 热销品类TOP5 -->
      <el-col :xs="24" :lg="12">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">🔥 热销品类 TOP5</span>
            </div>
          </template>
          <div ref="categoryChartRef" class="chart-container" style="height: 300px"></div>
        </el-card>
      </el-col>

      <!-- 近期订单列表 -->
      <el-col :xs="24" :lg="12">
        <el-card shadow="hover" class="recent-orders-card">
          <template #header>
            <div class="card-header">
              <span class="card-title">📝 近期订单</span>
              <el-button link type="primary" @click="goToOrders">查看全部</el-button>
            </div>
          </template>
          <el-table :data="recentOrders" stripe max-height="300">
            <el-table-column prop="order_no" label="订单号" width="120" />
            <el-table-column prop="customer_name" label="客户" min-width="100" show-overflow-tooltip />
            <el-table-column prop="total_amount" label="金额" width="100" align="right">
              <template #default="{ row }">¥{{ formatAmount(row.total_amount) }}</template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80" align="center">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" size="small">
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 线路汇总 -->
    <el-card shadow="hover" class="route-summary-card">
      <template #header>
        <div class="card-header">
          <span>线路汇总</span>
          <el-date-picker
            v-model="summaryDate"
            type="date"
            placeholder="选择日期"
            size="small"
            value-format="YYYY-MM-DD"
            @change="loadRouteSummary"
          />
        </div>
      </template>
      
      <el-table :data="routeSummary" border stripe>
        <el-table-column prop="name" label="线路/销售员" min-width="150" />
        <el-table-column prop="order_count" label="订单数" width="120" align="center" />
        <el-table-column prop="total_amount" label="总金额" width="150" align="right">
          <template #default="{ row }">
            ¥{{ formatAmount(row.total_amount) }}
          </template>
        </el-table-column>
        <el-table-column label="占比" min-width="150">
          <template #default="{ row }">
            <el-progress 
              :percentage="calculatePercentage(row.total_amount)" 
              :color="getProgressColor(calculatePercentage(row.total_amount))"
            />
          </template>
        </el-table-column>
      </el-table>
      
      <div class="summary-footer">
        <el-descriptions :column="3" border>
          <el-descriptions-item label="总订单数">
            <strong>{{ routeSummaryTotal.orders }}</strong>
          </el-descriptions-item>
          <el-descriptions-item label="总金额">
            <strong style="color: #f5576c">¥{{ formatAmount(routeSummaryTotal.amount) }}</strong>
          </el-descriptions-item>
          <el-descriptions-item label="平均客单价">
            <strong>¥{{ formatAmount(routeSummaryTotal.avgAmount) }}</strong>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { 
  getOverviewStats, 
  getSalesTrend, 
  getProductRanking, 
  getRouteSummary,
  getCustomerDistribution 
} from '../../../api/desktop/dashboard'
import { getOrders } from '../../../api/desktop/orders'

const router = useRouter()

// 刷新状态
const refreshing = ref(false)
const quickDate = ref(new Date().toISOString().split('T')[0])

// 统计数据
const dashboardStats = reactive({
  totalOrders: 0,
  totalAmount: 0,
  activeCustomers: 0,
  customersCount: 0,
  productsCount: 0,
  hotProducts: 0,
  orderGrowth: 0,
  amountGrowth: 0
})

// 销售趋势
const trendDays = ref(7)
const salesTrendChartRef = ref(null)
let salesTrendChart = null

// 订单状态分布
const orderStatusChartRef = ref(null)
let orderStatusChart = null

// 商品排行
const rankingPeriod = ref('week')
const productRankingChartRef = ref(null)
let productRankingChart = null

// 客户分布
const customerDistChartRef = ref(null)
let customerDistChart = null

// 热销品类
const categoryChartRef = ref(null)
let categoryChart = null

// 线路汇总
const summaryDate = ref(new Date().toISOString().split('T')[0])
const routeSummary = ref([])
const routeSummaryTotal = reactive({
  orders: 0,
  amount: 0,
  avgAmount: 0
})

// 近期订单
const recentOrders = ref([])

// 格式化金额
const formatAmount = (amount) => {
  return Number(amount).toFixed(2)
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

// 跳转到订单页面
const goToOrders = () => {
  router.push('/desktop/orders')
}

// 日期变化处理
const handleDateChange = (date) => {
  if (date) {
    summaryDate.value = date
    loadRouteSummary()
  }
}

// 刷新所有数据
const refreshAllData = async () => {
  refreshing.value = true
  try {
    await Promise.all([
      loadOverviewStats(),
      loadSalesTrend(),
      loadProductRanking(),
      loadCustomerDistribution(),
      loadRouteSummary(),
      loadRecentOrders()
    ])
    ElMessage.success('数据刷新成功')
  } catch (error) {
    ElMessage.error('数据刷新失败')
  } finally {
    refreshing.value = false
  }
}

// 导出报表
const exportDashboard = () => {
  ElMessage.info('导出功能开发中...')
  // TODO: 实现导出功能
}

// 计算百分比
const calculatePercentage = (amount) => {
  if (routeSummaryTotal.amount === 0) return 0
  return Math.round((amount / routeSummaryTotal.amount) * 100)
}

// 获取进度条颜色
const getProgressColor = (percentage) => {
  if (percentage >= 50) return '#67c23a'
  if (percentage >= 30) return '#e6a23c'
  return '#f56c6c'
}

// 加载概览数据
const loadOverviewStats = async () => {
  try {
    const res = await getOverviewStats('today')
    if (res.success) {
      const stats = res.stats
      dashboardStats.totalOrders = stats.total_orders || 0
      dashboardStats.totalAmount = stats.total_amount || 0
      dashboardStats.activeCustomers = stats.customers_count || 0
      dashboardStats.customersCount = stats.customers_count || 0
      dashboardStats.productsCount = stats.products_count || 0
      dashboardStats.hotProducts = Math.floor(stats.products_count * 0.3) || 0
    }
  } catch (error) {
    console.error('加载概览数据失败', error)
  }
}

// 加载销售趋势
const loadSalesTrend = async () => {
  try {
    const res = await getSalesTrend(trendDays.value)
    if (res.success) {
      renderSalesTrendChart(res.data)
    }
  } catch (error) {
    console.error('加载销售趋势失败', error)
  }
}

// 渲染销售趋势图
const renderSalesTrendChart = (data) => {
  if (!salesTrendChartRef.value) return
  
  if (!salesTrendChart) {
    salesTrendChart = echarts.init(salesTrendChartRef.value)
  }

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#eee',
      borderWidth: 1,
      textStyle: {
        color: '#333'
      }
    },
    legend: {
      data: ['订单数', '销售额'],
      top: 10,
      textStyle: {
        fontSize: 12
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '10%',
      top: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: data.dates || [],
      axisLabel: {
        rotate: 45,
        interval: 'auto',
        fontSize: 11,
        color: '#666'
      }
    },
    yAxis: [
      {
        type: 'value',
        name: '订单数',
        position: 'left',
        nameTextStyle: {
          fontSize: 12,
          color: '#666'
        },
        axisLabel: {
          fontSize: 11,
          color: '#666'
        }
      },
      {
        type: 'value',
        name: '销售额',
        position: 'right',
        nameTextStyle: {
          fontSize: 12,
          color: '#666'
        },
        axisLabel: {
          fontSize: 11,
          color: '#666',
          formatter: '￥{value}'
        }
      }
    ],
    series: [
      {
        name: '订单数',
        type: 'line',
        smooth: true,
        data: data.order_counts || [],
        itemStyle: {
          color: '#667eea'
        },
        lineStyle: {
          width: 2
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(102, 126, 234, 0.5)' },
            { offset: 1, color: 'rgba(102, 126, 234, 0.1)' }
          ])
        }
      },
      {
        name: '销售额',
        type: 'line',
        smooth: true,
        yAxisIndex: 1,
        data: data.amounts || [],
        itemStyle: {
          color: '#f5576c'
        },
        lineStyle: {
          width: 2
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(245, 87, 108, 0.5)' },
            { offset: 1, color: 'rgba(245, 87, 108, 0.1)' }
          ])
        }
      }
    ]
  }

  salesTrendChart.setOption(option)
}

// 加载商品排行
const loadProductRanking = async () => {
  try {
    const res = await getProductRanking(10, rankingPeriod.value)
    if (res.success) {
      renderProductRankingChart(res.data)
    }
  } catch (error) {
    console.error('加载商品排行失败', error)
  }
}

// 渲染商品排行图
const renderProductRankingChart = (data) => {
  if (!productRankingChartRef.value) return
  
  if (!productRankingChart) {
    productRankingChart = echarts.init(productRankingChartRef.value)
  }

  const products = (data.products || []).reverse()
  const quantities = (data.quantities || []).reverse()

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#eee',
      borderWidth: 1,
      textStyle: {
        color: '#333'
      }
    },
    grid: {
      left: '3%',
      right: '8%',
      bottom: '3%',
      top: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      name: '销量',
      nameTextStyle: {
        fontSize: 12,
        color: '#666'
      },
      axisLabel: {
        fontSize: 11,
        color: '#666'
      }
    },
    yAxis: {
      type: 'category',
      data: products,
      axisLabel: {
        interval: 0,
        fontSize: 12,
        color: '#666',
        formatter: (value) => {
          // 智能截断，避免重叠
          if (value.length > 12) {
            return value.substring(0, 12) + '...'
          }
          return value
        }
      }
    },
    series: [
      {
        name: '销量',
        type: 'bar',
        data: quantities,
        barWidth: '60%',
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#4facfe' },
            { offset: 1, color: '#00f2fe' }
          ]),
          borderRadius: [0, 4, 4, 0]
        },
        label: {
          show: true,
          position: 'right',
          fontSize: 11,
          color: '#666'
        }
      }
    ]
  }

  productRankingChart.setOption(option)
}

// 加载订单状态分布
const loadOrderStatus = async () => {
  try {
    // 从概览数据中获取状态分布
    const res = await getOverviewStats('today')
    if (res.success) {
      const statusData = res.stats.status_breakdown || {}
      renderOrderStatusChart(statusData)
    }
  } catch (error) {
    console.error('加载订单状态失败', error)
  }
}

// 渲染订单状态图
const renderOrderStatusChart = (statusData) => {
  if (!orderStatusChartRef.value) return
  
  if (!orderStatusChart) {
    orderStatusChart = echarts.init(orderStatusChartRef.value)
  }

  const statusMap = {
    pending: '待处理',
    completed: '已完成',
    cancelled: '已取消'
  }

  const data = Object.entries(statusData).map(([key, value]) => ({
    name: statusMap[key] || key,
    value: value
  }))

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#eee',
      borderWidth: 1,
      textStyle: {
        color: '#333'
      }
    },
    legend: {
      orient: 'vertical',
      right: 10,
      top: 'center',
      textStyle: {
        fontSize: 12,
        color: '#666'
      }
    },
    series: [
      {
        name: '订单状态',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['35%', '50%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 8,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          position: 'outside',
          formatter: '{b}\n{c}',
          fontSize: 12,
          color: '#666'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold'
          }
        },
        data: data.length > 0 ? data : [
          { name: '待处理', value: 0 },
          { name: '已完成', value: 0 },
          { name: '已取消', value: 0 }
        ],
        color: ['#f59e0b', '#10b981', '#ef4444']
      }
    ]
  }

  orderStatusChart.setOption(option)
}

// 加载客户分布
const loadCustomerDistribution = async () => {
  try {
    const res = await getCustomerDistribution()
    if (res.success) {
      renderCustomerDistChart(res.data)
    }
  } catch (error) {
    console.error('加载客户分布失败', error)
  }
}

// 渲染客户分布图
const renderCustomerDistChart = (data) => {
  if (!customerDistChartRef.value) return
  
  if (!customerDistChart) {
    customerDistChart = echarts.init(customerDistChartRef.value)
  }

  const chartData = (data.labels || []).map((label, index) => ({
    name: label,
    value: data.values[index] || 0
  }))

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c}人 ({d}%)',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#eee',
      borderWidth: 1,
      textStyle: {
        color: '#333'
      }
    },
    legend: {
      orient: 'vertical',
      right: 10,
      top: 'center',
      textStyle: {
        fontSize: 12,
        color: '#666'
      }
    },
    series: [
      {
        name: '客户分布',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['35%', '50%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 8,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          position: 'outside',
          formatter: '{b}\n{c}人',
          fontSize: 12,
          color: '#666'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold'
          }
        },
        data: chartData.length > 0 ? chartData : [
          { name: '暂无数据', value: 0 }
        ],
        color: ['#667eea', '#f5576c', '#4facfe', '#43e97b', '#fa709a']
      }
    ]
  }

  customerDistChart.setOption(option)
}

// 加载热销品类（模拟数据，实际应从后端获取）
const loadCategoryStats = async () => {
  // TODO: 添加后端API获取品类统计
  // 暂时使用模拟数据
  const mockData = {
    categories: ['蔬菜', '水果', '肉类', '海鲜', '粮油'],
    values: [35, 28, 22, 18, 15]
  }
  renderCategoryChart(mockData)
}

// 渲染热销品类图
const renderCategoryChart = (data) => {
  if (!categoryChartRef.value) return
  
  if (!categoryChart) {
    categoryChart = echarts.init(categoryChartRef.value)
  }

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#eee',
      borderWidth: 1,
      textStyle: {
        color: '#333'
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: data.categories || [],
      axisLabel: {
        fontSize: 12,
        color: '#666'
      }
    },
    yAxis: {
      type: 'value',
      name: '销量',
      nameTextStyle: {
        fontSize: 12,
        color: '#666'
      },
      axisLabel: {
        fontSize: 11,
        color: '#666'
      }
    },
    series: [
      {
        name: '销量',
        type: 'bar',
        data: data.values || [],
        barWidth: '50%',
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#fa709a' },
            { offset: 1, color: '#fee140' }
          ]),
          borderRadius: [4, 4, 0, 0]
        },
        label: {
          show: true,
          position: 'top',
          fontSize: 11,
          color: '#666'
        }
      }
    ]
  }

  categoryChart.setOption(option)
}

// 加载线路汇总
const loadRouteSummary = async () => {
  try {
    const res = await getRouteSummary(summaryDate.value)
    if (res.success) {
      routeSummary.value = res.data.routes || []
      routeSummaryTotal.orders = res.data.total_orders || 0
      routeSummaryTotal.amount = res.data.total_amount || 0
      routeSummaryTotal.avgAmount = res.data.total_orders > 0 
        ? res.data.total_amount / res.data.total_orders 
        : 0
    }
  } catch (error) {
    console.error('加载线路汇总失败', error)
  }
}

// 加载近期订单
const loadRecentOrders = async () => {
  try {
    const res = await getOrders({ page: 1, page_size: 5 })
    if (res.success) {
      recentOrders.value = res.orders || []
    }
  } catch (error) {
    console.error('加载近期订单失败', error)
  }
}

onMounted(async () => {
  await loadOverviewStats()
  await loadSalesTrend()
  await loadProductRanking()
  await loadOrderStatus()
  await loadCustomerDistribution()
  await loadCategoryStats()
  await loadRouteSummary()
  await loadRecentOrders()
  
  // 窗口大小变化时重新渲染图表
  window.addEventListener('resize', () => {
    salesTrendChart?.resize()
    orderStatusChart?.resize()
    productRankingChart?.resize()
    customerDistChart?.resize()
    categoryChart?.resize()
  })
})
</script>

<style scoped lang="scss">
.dashboard-page {
  .action-bar {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
    align-items: center;
    flex-wrap: wrap;
  }

  .stats-cards {
    margin-bottom: 20px;
    
    .stat-card {
      transition: all 0.3s;
      
      &:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
      }
      
      .stat-item {
        display: flex;
        align-items: center;
        gap: 15px;
        
        .stat-icon {
          width: 60px;
          height: 60px;
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #fff;
          font-size: 28px;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }
        
        .stat-content {
          flex: 1;
          
          .stat-value {
            font-size: 28px;
            font-weight: bold;
            color: #1e293b;
            line-height: 1;
          }
          
          .stat-label {
            font-size: 14px;
            color: #64748b;
            margin-top: 8px;
          }
          
          .stat-sub {
            font-size: 12px;
            color: #94a3b8;
            margin-top: 4px;
          }
          
          .stat-trend {
            font-size: 12px;
            margin-top: 4px;
            
            .trend-up {
              color: #10b981;
            }
            
            .trend-down {
              color: #ef4444;
            }
          }
        }
      }
    }
  }

  .charts-section {
    margin-bottom: 20px;
  }

  .chart-card {
    transition: all 0.3s;
    
    &:hover {
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
    }
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .card-title {
      font-size: 16px;
      font-weight: 600;
      color: #1e293b;
    }
  }

  .chart-container {
    width: 100%;
  }

  .recent-orders-card {
    transition: all 0.3s;
    
    &:hover {
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
    }
  }

  .route-summary-card {
    .summary-footer {
      margin-top: 20px;
    }
  }
}

// 响应式优化
@media (max-width: 768px) {
  .dashboard-page {
    .action-bar {
      flex-direction: column;
      align-items: stretch;
      
      .el-button,
      .el-date-picker {
        width: 100%;
      }
    }
    
    .stats-cards {
      .stat-card {
        margin-bottom: 10px;
      }
    }
    
    .card-header {
      flex-direction: column;
      gap: 10px;
      align-items: flex-start;
    }
  }
}
</style>

﻿﻿﻿<template>
  <div class="dashboard">
    <h2 class="page-title">数据概览</h2>
    
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card purple">
          <div class="stat-icon"><el-icon><User /></el-icon></div>
          <div class="stat-info">
            <div class="stat-label">总用户数</div>
            <div class="stat-value">{{ stats.total_users }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card green">
          <div class="stat-icon"><el-icon><Key /></el-icon></div>
          <div class="stat-info">
            <div class="stat-label">活跃授权</div>
            <div class="stat-value">{{ stats.active_licenses }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card orange">
          <div class="stat-icon"><el-icon><ShoppingCart /></el-icon></div>
          <div class="stat-info">
            <div class="stat-label">本月订单</div>
            <div class="stat-value">{{ salesSummary.total_orders }}</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card blue">
          <div class="stat-icon"><el-icon><Wallet /></el-icon></div>
          <div class="stat-info">
            <div class="stat-label">本月收入</div>
            <div class="stat-value">¥{{ salesSummary.total_amount.toLocaleString() }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="chart-row">
      <!-- 销售趋势图 -->
      <el-col :span="14">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>销售趋势</span>
              <div class="header-actions">
                <el-button-group>
                  <el-button 
                    v-for="p in periods" 
                    :key="p.value"
                    :type="period === p.value ? 'primary' : 'default'"
                    size="small"
                    @click="period = p.value"
                  >
                    {{ p.label }}
                  </el-button>
                </el-button-group>
              </div>
            </div>
          </template>
          <div ref="salesTrendChart" class="chart-container"></div>
        </el-card>
      </el-col>
      
      <!-- 商品销量排名 -->
      <el-col :span="10">
        <el-card class="chart-card">
          <template #header>
            <span>商品销量排名</span>
          </template>
          <div ref="productChart" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 数据表格区域 -->
    <el-row :gutter="20" class="table-row">
      <!-- 销售统�?-->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>销售员业绩</span>
          </template>
          <el-table :data="salesSummary.sales_stats" stripe size="small">
            <el-table-column prop="sales_person" label="销售员" />
            <el-table-column prop="order_count" label="订单数" />
            <el-table-column prop="customer_count" label="客户数" />
            <el-table-column prop="total_amount" label="销售额">
              <template #default="{ row }">
                ¥{{ row.total_amount.toLocaleString() }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      
      <!-- 客户活跃度 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>客户活跃度</span>
          </template>
          <el-table :data="customerActivity.customers.slice(0, 10)" stripe size="small">
            <el-table-column prop="customer_name" label="客户" />
            <el-table-column prop="order_count" label="订单数" />
            <el-table-column prop="total_amount" label="消费金额">
              <template #default="{ row }">
                ¥{{ row.total_amount.toLocaleString() }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 最近活动 -->
    <el-card class="activity-card">
      <template #header>
        <div class="card-header">
          <span>最近活动</span>
        </div>
      </template>
      <el-timeline>
        <el-timeline-item
          v-for="(activity, index) in activities"
          :key="index"
          :timestamp="formatDateTime(activity.created_at)"
          :type="getActivityType(activity.action)"
        >
          <div class="activity-content">
            <strong>{{ activity.username || '系统' }}</strong>
            <span class="activity-action">{{ getActivityLabel(activity.action) }}</span>
            <span>{{ activity.description }}</span>
          </div>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-if="activities.length === 0" description="暂无活动记录" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import { User, Key, ShoppingCart, Wallet } from '@element-plus/icons-vue'
import {
  getSystemStats,
  getSalesSummary,
  getProductSales,
  getCustomerActivity,
  getRecentActivities
} from '../../api/admin/dashboard'
import dayjs from 'dayjs'

const salesTrendChart = ref(null)
const productChart = ref(null)
let salesChartInstance = null
let productChartInstance = null

const periods = [
  { label: '本周', value: 'week' },
  { label: '本月', value: 'month' },
  { label: '本季度', value: 'quarter' }
]

const period = ref('month')

const stats = reactive({
  total_users: 0,
  active_users: 0,
  total_licenses: 0,
  active_licenses: 0,
  revoked_licenses: 0,
  expiring_soon: 0
})

const salesSummary = reactive({
  total_orders: 0,
  total_amount: 0,
  sales_stats: []
})

const productSales = ref([])
const customerActivity = reactive({
  total_orders: 0,
  active_customers: 0,
  customers: []
})

const activities = ref([])

const loadAllData = async () => {
  await Promise.all([
    loadSystemStats(),
    loadSalesSummary(),
    loadProductSales(),
    loadCustomerActivity(),
    loadRecentActivities()
  ])
}

const loadSystemStats = async () => {
  try {
    const res = await getSystemStats()
    if (res.success) {
      Object.assign(stats, res.stats)
    }
  } catch (error) {
    console.error('加载系统统计失败:', error)
  }
}

const loadSalesSummary = async () => {
  try {
    const res = await getSalesSummary({
      start_date: getStartDate(period.value),
      end_date: dayjs().format('YYYY-MM-DD')
    })
    if (res.success) {
      Object.assign(salesSummary, res.summary)
    }
  } catch (error) {
    console.error('加载销售汇总失�?', error)
  }
}

const loadProductSales = async () => {
  try {
    const res = await getProductSales({
      start_date: getStartDate(period.value),
      end_date: dayjs().format('YYYY-MM-DD'),
      limit: 10
    })
    if (res.success) {
      productSales.value = res.products || []
    }
  } catch (error) {
    console.error('加载商品销售失�?', error)
  }
}

const loadCustomerActivity = async () => {
  try {
    const res = await getCustomerActivity({
      start_date: getStartDate(period.value),
      end_date: dayjs().format('YYYY-MM-DD')
    })
    if (res.success) {
      Object.assign(customerActivity, res.summary)
    }
  } catch (error) {
    console.error('加载客户活动失败:', error)
  }
}

const loadRecentActivities = async () => {
  try {
    const res = await getRecentActivities()
    if (res.success) {
      activities.value = res.activities || []
    }
  } catch (error) {
    console.error('加载最近活动失�?', error)
  }
}

const getStartDate = (period) => {
  const now = dayjs()
  switch (period) {
    case 'week':
      return now.startOf('week').format('YYYY-MM-DD')
    case 'month':
      return now.startOf('month').format('YYYY-MM-DD')
    case 'quarter':
      return now.startOf('quarter').format('YYYY-MM-DD')
    default:
      return now.startOf('month').format('YYYY-MM-DD')
  }
}

const initCharts = () => {
  if (salesTrendChart.value) {
    salesChartInstance = echarts.init(salesTrendChart.value)
    updateSalesChart()
  }
  if (productChart.value) {
    productChartInstance = echarts.init(productChart.value)
    updateProductChart()
  }
}

const updateSalesChart = () => {
  if (!salesChartInstance) return
  
  const days = period.value === 'week' ? 7 : period.value === 'month' ? 30 : 90
  const dates = []
  const amounts = []
  const orders = []
  
  for (let i = days - 1; i >= 0; i--) {
    const date = dayjs().subtract(i, 'day')
    dates.push(date.format('MM-DD'))
    amounts.push(Math.floor(Math.random() * 5000) + 1000)
    orders.push(Math.floor(Math.random() * 50) + 5)
  }
  
  salesChartInstance.setOption({
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: ['销售额', '订单数'],
      top: 0
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: 40,
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates
    },
    yAxis: [
      {
        type: 'value',
        name: '销售额(元)',
        splitLine: { show: false }
      },
      {
        type: 'value',
        name: '订单数',
        splitLine: { show: false }
      }
    ],
    series: [
      {
        name: '销售额',
        type: 'line',
        smooth: true,
        areaStyle: {
          opacity: 0.1
        },
        data: amounts,
        color: '#409EFF'
      },
      {
        name: '订单数',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        areaStyle: {
          opacity: 0.1
        },
        data: orders,
        color: '#67C23A'
      }
    ]
  })
}

const updateProductChart = () => {
  if (!productChartInstance) return
  
  const products = productSales.value.length > 0 
    ? productSales.value 
    : [
        { product_name: '商品A', total_quantity: 150 },
        { product_name: '商品B', total_quantity: 120 },
        { product_name: '商品C', total_quantity: 90 },
        { product_name: '商品D', total_quantity: 70 },
        { product_name: '商品E', total_quantity: 50 }
      ]
  
  productChartInstance.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: 10,
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: products.map(p => p.product_name),
      axisLabel: {
        rotate: 30,
        fontSize: 11
      }
    },
    yAxis: {
      type: 'value',
      splitLine: { show: false }
    },
    series: [
      {
        type: 'bar',
        data: products.map(p => p.total_quantity),
        itemStyle: {
          borderRadius: [4, 4, 0, 0],
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#667eea' },
            { offset: 1, color: '#764ba2' }
          ])
        }
      }
    ]
  })
}

const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  return dayjs(dateStr).format('MM-DD HH:mm')
}

const getActivityLabel = (action) => {
  const labels = {
    login: '登录',
    logout: '登出',
    create: '创建',
    update: '更新',
    delete: '删除',
    export: '导出',
    generate: '生成',
    extend: '展期',
    revoke: '撤销'
  }
  return labels[action] || action
}

const getActivityType = (action) => {
  const types = {
    login: 'success',
    logout: 'info',
    create: 'primary',
    update: 'warning',
    delete: 'danger',
    export: 'info',
    generate: 'success',
    extend: 'success',
    revoke: 'danger'
  }
  return types[action] || 'info'
}

const handleResize = () => {
  salesChartInstance?.resize()
  productChartInstance?.resize()
}

watch(period, () => {
  loadAllData()
  nextTick(() => {
    updateSalesChart()
    updateProductChart()
  })
})

onMounted(() => {
  loadAllData()
  nextTick(() => {
    initCharts()
  })
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  salesChartInstance?.dispose()
  productChartInstance?.dispose()
})
</script>

<style scoped lang="scss">
.dashboard {
  .page-title {
    font-size: 24px;
    margin-bottom: 20px;
    color: #303133;
  }
  
  .stats-row {
    margin-bottom: 20px;
    
    .stat-card {
      color: #fff;
      padding: 20px;
      display: flex;
      align-items: center;
      gap: 15px;
      transition: transform 0.2s, box-shadow 0.2s;
      
      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      }
      
      &.purple {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      }
      
      &.green {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
      }
      
      &.orange {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
      }
      
      &.blue {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
      }
      
      .stat-icon {
        font-size: 32px;
        opacity: 0.9;
      }
      
      .stat-info {
        flex: 1;
        
        .stat-label {
          font-size: 14px;
          opacity: 0.9;
          margin-bottom: 4px;
        }
        
        .stat-value {
          font-size: 28px;
          font-weight: bold;
        }
      }
    }
  }
  
  .chart-row {
    margin-bottom: 20px;
    
    .chart-card {
      ::deep(.el-card__header) {
        padding: 15px 20px;
        border-bottom: 1px solid #ebeef5;
      }
      
      .chart-container {
        height: 280px;
      }
    }
  }
  
  .table-row {
    margin-bottom: 20px;
  }
  
  .activity-card {
    ::deep(.el-card__header) {
      padding: 15px 20px;
      border-bottom: 1px solid #ebeef5;
    }
    
    .activity-content {
      line-height: 1.8;
      
      .activity-action {
        margin: 0 8px;
        color: #409EFF;
      }
    }
  }
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .header-actions {
      display: flex;
      gap: 10px;
    }
  }
}
</style>
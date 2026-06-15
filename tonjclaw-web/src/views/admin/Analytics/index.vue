﻿﻿﻿<template>
  <div class="analytics-page">
    <div class="page-header">
      <h2 class="page-title">数据统计与分析</h2>
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

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon blue">
              <el-icon><Wallet /></el-icon>
            </div>
            <div class="stat-info">
              <p class="stat-value">{{ formatCurrency(salesSummary.total_revenue) }}</p>
              <p class="stat-label">总销售额</p>
              <p class="stat-change" :class="salesSummary.revenue_change >= 0 ? 'positive' : 'negative'">
                <el-icon><TrendCharts v-if="salesSummary.revenue_change >= 0" /><ArrowDown v-else /></el-icon>
                {{ Math.abs(salesSummary.revenue_change) }}%
              </p>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon green">
              <el-icon><ShoppingCart /></el-icon>
            </div>
            <div class="stat-info">
              <p class="stat-value">{{ salesSummary.total_orders }}</p>
              <p class="stat-label">订单总数</p>
              <p class="stat-change" :class="salesSummary.order_change >= 0 ? 'positive' : 'negative'">
                <el-icon><TrendCharts v-if="salesSummary.order_change >= 0" /><ArrowDown v-else /></el-icon>
                {{ Math.abs(salesSummary.order_change) }}%
              </p>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon orange">
              <el-icon><User /></el-icon>
            </div>
            <div class="stat-info">
              <p class="stat-value">{{ salesSummary.new_users }}</p>
              <p class="stat-label">新增用户</p>
              <p class="stat-change" :class="salesSummary.user_change >= 0 ? 'positive' : 'negative'">
                <el-icon><TrendCharts v-if="salesSummary.user_change >= 0" /><ArrowDown v-else /></el-icon>
                {{ Math.abs(salesSummary.user_change) }}%
              </p>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon purple">
              <el-icon><Ticket /></el-icon>
            </div>
            <div class="stat-info">
              <p class="stat-value">{{ salesSummary.total_licenses }}</p>
              <p class="stat-label">授权码总数</p>
              <p class="stat-change" :class="salesSummary.license_change >= 0 ? 'positive' : 'negative'">
                <el-icon><TrendCharts v-if="salesSummary.license_change >= 0" /><ArrowDown v-else /></el-icon>
                {{ Math.abs(salesSummary.license_change) }}%
              </p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="chart-row">
      <el-col :span="14">
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>销售趋势</span>
            </div>
          </template>
          <div ref="salesTrendChart" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card class="chart-card">
          <template #header>
            <span>用户增长趋势</span>
          </template>
          <div ref="userGrowthChart" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="chart-row">
      <el-col :span="14">
        <el-card class="chart-card">
          <template #header>
            <span>产品销售排名</span>
          </template>
          <div ref="productRankingChart" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card class="chart-card">
          <template #header>
            <span>销售渠道分析</span>
          </template>
          <div ref="channelChart" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 数据表格 -->
    <el-card class="table-card">
      <template #header>
        <div class="card-header">
          <span>销售明细</span>
          <el-button type="primary" size="small" @click="handleExport">
            <el-icon><Download /></el-icon> 导出报表
          </el-button>
        </div>
      </template>
      <el-table :data="salesDetails" v-loading="loading">
        <el-table-column prop="date" label="日期" width="120" />
        <el-table-column prop="orders" label="订单数" width="100" />
        <el-table-column prop="revenue" label="销售额" width="120">
          <template #default="{ row }">{{ formatCurrency(row.revenue) }}</template>
        </el-table-column>
        <el-table-column prop="new_users" label="新增用户" width="100" />
        <el-table-column prop="avg_order_value" label="客单价" width="120">
          <template #default="{ row }">{{ formatCurrency(row.avg_order_value) }}</template>
        </el-table-column>
        <el-table-column prop="conversion_rate" label="转化率" width="100">
          <template #default="{ row }">{{ (row.conversion_rate * 100).toFixed(2) }}%</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Wallet, ShoppingCart, User, Ticket, TrendCharts, ArrowDown, Download } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { 
  getSalesSummary, 
  getSalesTrend,
  getUserGrowth,
  getProductSales,
  getSalesDetails
} from '../../../api/admin/dashboard'

const period = ref('month')
const loading = ref(false)

const periods = [
  { label: '今日', value: 'today' },
  { label: '本周', value: 'week' },
  { label: '本月', value: 'month' },
  { label: '本季度', value: 'quarter' },
  { label: '本年', value: 'year' }
]

const salesSummary = reactive({
  total_revenue: 0,
  total_orders: 0,
  new_users: 0,
  total_licenses: 0,
  revenue_change: 0,
  order_change: 0,
  user_change: 0,
  license_change: 0
})

const salesDetails = ref([])

let salesTrendChart = null
let userGrowthChart = null
let productRankingChart = null
let channelChart = null

const salesTrendChartRef = ref(null)
const userGrowthChartRef = ref(null)
const productRankingChartRef = ref(null)
const channelChartRef = ref(null)

const formatCurrency = (value) => {
  if (!value) return '¥0.00'
  return `¥${parseFloat(value).toFixed(2)}`
}

const loadSalesSummary = async () => {
  try {
    const res = await getSalesSummary({ period: period.value })
    if (res.success) {
      Object.assign(salesSummary, res.data)
    }
  } catch (error) {
    console.error('加载销售汇总失�?', error)
  }
}

const loadSalesTrend = async () => {
  try {
    const res = await getSalesTrend({ period: period.value })
    if (res.success && salesTrendChart) {
      const data = res.data
      salesTrendChart.setOption({
        tooltip: {
          trigger: 'axis',
          formatter: (params) => {
            let result = params[0].name + '<br/>'
            params.forEach(param => {
              result += `${param.marker} ${param.seriesName}: ¥${param.value.toFixed(2)}<br/>`
            })
            return result
          }
        },
        legend: {
          data: ['销售额', '订单数'],
          bottom: 0
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '15%',
          top: '10%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: data.dates,
          axisLabel: { rotate: 30 }
        },
        yAxis: [
          { type: 'value', name: '销售额' },
          { type: 'value', name: '订单数' }
        ],
        series: [
          {
            name: '销售额',
            type: 'line',
            smooth: true,
            data: data.revenues,
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
                { offset: 1, color: 'rgba(64, 158, 255, 0.05)' }
              ])
            }
          },
          {
            name: '订单数',
            type: 'line',
            smooth: true,
            yAxisIndex: 1,
            data: data.orders
          }
        ]
      })
    }
  } catch (error) {
    console.error('加载销售趋势失�?', error)
  }
}

const loadUserGrowth = async () => {
  try {
    const res = await getUserGrowth({ period: period.value })
    if (res.success && userGrowthChart) {
      const data = res.data
      userGrowthChart.setOption({
        tooltip: {
          trigger: 'axis',
          formatter: (params) => {
            let result = params[0].name + '<br/>'
            params.forEach(param => {
              result += `${param.marker} ${param.seriesName}: ${param.value}�?br/>`
            })
            return result
          }
        },
        legend: {
          data: ['新增用户', '累计用户'],
          bottom: 0
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '15%',
          top: '10%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: data.dates,
          axisLabel: { rotate: 30 }
        },
        yAxis: [
          { type: 'value', name: '新增用户' },
          { type: 'value', name: '累计用户' }
        ],
        series: [
          {
            name: '新增用户',
            type: 'bar',
            data: data.new_users
          },
          {
            name: '累计用户',
            type: 'line',
            smooth: true,
            yAxisIndex: 1,
            data: data.total_users
          }
        ]
      })
    }
  } catch (error) {
    console.error('加载用户增长失败:', error)
  }
}

const loadProductSales = async () => {
  try {
    const res = await getProductSales({ period: period.value })
    if (res.success && productRankingChart) {
      const data = res.data
      productRankingChart.setOption({
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          formatter: (params) => {
            const param = params[0]
            return `${param.name}<br/>${param.marker} 销售额: ¥${param.value.toFixed(2)}`
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
          type: 'value',
          name: '销售额'
        },
        yAxis: {
          type: 'category',
          data: data.products.reverse()
        },
        series: [{
          type: 'bar',
          data: data.revenues.reverse(),
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: '#FF9800' },
              { offset: 1, color: '#FFC107' }
            ])
          }
        }]
      })
    }
  } catch (error) {
    console.error('加载产品销售失�?', error)
  }
}

const loadChannelData = async () => {
  try {
    const res = await getSalesSummary({ period: period.value })
    if (res.success && channelChart) {
      const channels = [
        { name: '官网', value: res.data.channel_website || 0 },
        { name: '代理', value: res.data.channel_agent || 0 },
        { name: '分销', value: res.data.channel_distributor || 0 },
        { name: '其他', value: res.data.channel_other || 0 }
      ].filter(c => c.value > 0)
      
      channelChart.setOption({
        tooltip: {
          trigger: 'item',
          formatter: '{a} <br/>{b}: ¥{c.toFixed(2)} ({d}%)'
        },
        legend: {
          orient: 'vertical',
          left: 'left',
          top: 'center'
        },
        series: [{
          name: '销售渠道',
          type: 'pie',
          radius: ['40%', '70%'],
          center: ['60%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 10,
            borderColor: '#fff',
            borderWidth: 2
          },
          label: {
            show: false
          },
          emphasis: {
            label: { show: true, fontSize: 16, fontWeight: 'bold' }
          },
          data: channels
        }]
      })
    }
  } catch (error) {
    console.error('加载渠道数据失败:', error)
  }
}

const loadSalesDetails = async () => {
  loading.value = true
  try {
    const res = await getSalesDetails({ period: period.value })
    if (res.success) {
      salesDetails.value = res.data || []
    }
  } catch (error) {
    console.error('加载销售明细失�?', error)
  } finally {
    loading.value = false
  }
}

const handleExport = () => {
  ElMessage.success('报表导出功能开发中')
}

const initCharts = () => {
  if (salesTrendChartRef.value) {
    salesTrendChart = echarts.init(salesTrendChartRef.value)
  }
  if (userGrowthChartRef.value) {
    userGrowthChart = echarts.init(userGrowthChartRef.value)
  }
  if (productRankingChartRef.value) {
    productRankingChart = echarts.init(productRankingChartRef.value)
  }
  if (channelChartRef.value) {
    channelChart = echarts.init(channelChartRef.value)
  }
}

const resizeCharts = () => {
  salesTrendChart?.resize()
  userGrowthChart?.resize()
  productRankingChart?.resize()
  channelChart?.resize()
}

const loadAllData = async () => {
  await Promise.all([
    loadSalesSummary(),
    loadSalesTrend(),
    loadUserGrowth(),
    loadProductSales(),
    loadChannelData(),
    loadSalesDetails()
  ])
}

watch(period, () => {
  loadAllData()
})

onMounted(() => {
  initCharts()
  loadAllData()
  window.addEventListener('resize', resizeCharts)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeCharts)
  salesTrendChart?.dispose()
  userGrowthChart?.dispose()
  productRankingChart?.dispose()
  channelChart?.dispose()
})
</script>

<style scoped lang="scss">
.analytics-page {
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    
    .page-title {
      font-size: 24px;
      color: #303133;
      margin: 0;
    }
    
    .header-actions {
      display: flex;
      gap: 10px;
    }
  }
  
  .stats-row {
    margin-bottom: 20px;
  }
  
  .stat-card {
    ::deep(.el-card__body) {
      padding: 0;
    }
    
    .stat-content {
      display: flex;
      align-items: center;
      padding: 20px;
      gap: 15px;
    }
    
    .stat-icon {
      width: 56px;
      height: 56px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 28px;
      
      &.blue { background: linear-gradient(135deg, #e8f4fd 0%, #d4ebfa 100%); color: #409EFF; }
      &.green { background: linear-gradient(135deg, #f0f9eb 0%, #e1f3d8 100%); color: #67C23A; }
      &.orange { background: linear-gradient(135deg, #fff7e6 0%, #ffeeba 100%); color: #E6A23C; }
      &.purple { background: linear-gradient(135deg, #f3e8ff 0%, #e9d5ff 100%); color: #9B59B6; }
    }
    
    .stat-info {
      flex: 1;
      
      .stat-value {
        font-size: 24px;
        font-weight: bold;
        color: #303133;
        margin: 0;
      }
      
      .stat-label {
        font-size: 14px;
        color: #909399;
        margin: 4px 0;
      }
      
      .stat-change {
        font-size: 12px;
        display: flex;
        align-items: center;
        gap: 4px;
        margin: 0;
        
        &.positive { color: #67C23A; }
        &.negative { color: #F56C6C; }
      }
    }
  }
  
  .chart-row {
    margin-bottom: 20px;
  }
  
  .chart-card {
    ::deep(.el-card__body) {
      padding: 20px;
    }
    
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .chart-container {
      height: 300px;
    }
  }
  
  .table-card {
    ::deep(.el-card__body) {
      padding: 20px;
    }
    
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 15px;
    }
  }
}
</style>
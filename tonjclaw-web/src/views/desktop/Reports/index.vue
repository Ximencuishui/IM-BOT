<template>
  <div class="reports-page">
    <!-- 数据看板 -->
    <el-row :gutter="20" class="stats-cards">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-icon" style="background-color: #3b82f6">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ todayStats.orderCount || 0 }}</div>
              <div class="stat-label">今日订单数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-icon" style="background-color: #10b981">
              <el-icon><Coin /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">¥{{ todayStats.totalAmount || 0 }}</div>
              <div class="stat-label">今日销售额</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-icon" style="background-color: #f59e0b">
              <el-icon><User /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ todayStats.customerCount || 0 }}</div>
              <div class="stat-label">活跃客户</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-item">
            <div class="stat-icon" style="background-color: #8b5cf6">
              <el-icon><Goods /></el-icon>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ todayStats.productCount || 0 }}</div>
              <div class="stat-label">销售商品数</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="charts-row">
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>订单趋势</span>
              <el-radio-group v-model="trendPeriod" size="small" @change="loadTrendChart">
                <el-radio-button label="7">近7天</el-radio-button>
                <el-radio-button label="30">近30天</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <div ref="trendChartRef" style="height: 300px"></div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>商品销量排行 Top 10</span>
          </template>
          <div ref="rankingChartRef" style="height: 300px"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 日报表 -->
    <el-card class="report-card">
      <template #header>
        <div class="card-header">
          <span>日报表</span>
          <div>
            <el-date-picker
              v-model="reportDate"
              type="date"
              placeholder="选择日期"
              value-format="YYYY-MM-DD"
              style="margin-right: 10px"
              @change="loadDailyReport"
            />
            <el-select v-model="filterRouteId" placeholder="全部线路" clearable style="width: 150px; margin-right: 10px" @change="loadDailyReport">
              <el-option
                v-for="route in routeList"
                :key="route.id"
                :label="route.route_name"
                :value="route.id"
              />
            </el-select>
            <el-select v-model="filterSalespersonId" placeholder="全部人员" clearable style="width: 150px; margin-right: 10px" @change="loadDailyReport">
              <el-option
                v-for="sp in salespersonList"
                :key="sp.id"
                :label="sp.name"
                :value="sp.id"
              />
            </el-select>
            <el-select v-model="filterProductCategory" placeholder="全部分类" clearable style="width: 150px; margin-right: 10px" @change="loadDailyReport">
              <el-option label="蔬菜" value="蔬菜" />
              <el-option label="水果" value="水果" />
              <el-option label="肉类" value="肉类" />
              <el-option label="其他" value="其他" />
            </el-select>
            <el-button type="success" @click="handleExport">
              <el-icon><Download /></el-icon>
              导出Excel
            </el-button>
          </div>
        </div>
      </template>

      <el-table
        v-loading="reportLoading"
        :data="dailyReport"
        border
        stripe
        style="width: 100%"
        show-summary
        :summary-method="getSummaries"
      >
        <el-table-column prop="route_name" label="线路" width="120" />
        <el-table-column prop="sales_person" label="销售" width="100" />
        <el-table-column prop="customer_name" label="客户" min-width="120" />
        <el-table-column prop="product_name" label="商品" min-width="150" />
        <el-table-column prop="quantity" label="数量" width="100" />
        <el-table-column prop="unit" label="单位" width="80" />
        <el-table-column prop="amount" label="金额" width="100">
          <template #default="{ row }">
            ¥{{ row.amount }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import { getDailyReport, exportReport, getSalesSummary, getProductRanking } from '../../../api/desktop/reports'
import { getRoutes } from '../../../api/desktop/customers'
import { getSalespersons } from '../../../api/desktop/salespersons'

const trendChartRef = ref(null)
const rankingChartRef = ref(null)
const reportLoading = ref(false)
const dailyReport = ref([])
const routeList = ref([])
const salespersonList = ref([])
const reportDate = ref(new Date().toISOString().split('T')[0])
const filterRouteId = ref(null)
const filterSalespersonId = ref(null)
const filterProductCategory = ref(null)
const trendPeriod = ref('7')

const todayStats = ref({
  orderCount: 0,
  totalAmount: 0,
  customerCount: 0,
  productCount: 0
})

let trendChart = null
let rankingChart = null

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

// 加载销售人员列表
const loadSalespersons = async () => {
  try {
    const res = await getSalespersons({ is_active: 'true' })
    if (res.success) {
      salespersonList.value = res.salespersons || []
    }
  } catch (error) {
    console.error('加载销售人员失败', error)
  }
}

// 加载日报表
const loadDailyReport = async () => {
  reportLoading.value = true
  try {
    const params = { date: reportDate.value }
    if (filterRouteId.value) {
      params.route_id = filterRouteId.value
    }
    if (filterSalespersonId.value) {
      params.salesperson_id = filterSalespersonId.value
    }
    if (filterProductCategory.value) {
      params.product_category = filterProductCategory.value
    }
    
    const res = await getDailyReport(params)
    if (res.success) {
      dailyReport.value = res.summary?.details || []
      todayStats.value = res.summary?.stats || {}
    }
  } catch (error) {
    ElMessage.error('加载报表失败')
  } finally {
    reportLoading.value = false
  }
}

// 加载趋势图
const loadTrendChart = async () => {
  try {
    const res = await getSalesSummary({ days: trendPeriod.value })
    if (res.success && res.chart_data) {
      initTrendChart(res.chart_data)
    }
  } catch (error) {
    console.error('加载趋势图失败', error)
  }
}

// 初始化趋势图
const initTrendChart = (data) => {
  if (!trendChartRef.value) return
  
  if (!trendChart) {
    trendChart = echarts.init(trendChartRef.value)
  }
  
  const option = {
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'category',
      data: data.dates || []
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        name: '订单数',
        type: 'line',
        data: data.order_counts || [],
        smooth: true,
        itemStyle: { color: '#3b82f6' }
      },
      {
        name: '销售额',
        type: 'line',
        data: data.amounts || [],
        smooth: true,
        itemStyle: { color: '#10b981' }
      }
    ]
  }
  
  trendChart.setOption(option)
}

// 加载商品排行图
const loadRankingChart = async () => {
  try {
    const res = await getProductRanking({ limit: 10 })
    if (res.success && res.products) {
      initRankingChart(res.products)
    }
  } catch (error) {
    console.error('加载排行图失败', error)
  }
}

// 初始化排行图
const initRankingChart = (products) => {
  if (!rankingChartRef.value) return
  
  if (!rankingChart) {
    rankingChart = echarts.init(rankingChartRef.value)
  }
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'value'
    },
    yAxis: {
      type: 'category',
      data: products.map(p => p.product_name).reverse()
    },
    series: [
      {
        name: '销量',
        type: 'bar',
        data: products.map(p => p.total_quantity).reverse(),
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#8b5cf6' },
            { offset: 1, color: '#a78bfa' }
          ])
        }
      }
    ]
  }
  
  rankingChart.setOption(option)
}

// 导出Excel
const handleExport = async () => {
  try {
    const params = { date: reportDate.value }
    if (filterRouteId.value) {
      params.route_id = filterRouteId.value
    }
    if (filterSalespersonId.value) {
      params.salesperson_id = filterSalespersonId.value
    }
    if (filterProductCategory.value) {
      params.product_category = filterProductCategory.value
    }
    
    const res = await exportReport(params)
    const blob = new Blob([res], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `日报表_${reportDate.value}.xlsx`
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

// 表格合计
const getSummaries = (param) => {
  const { columns, data } = param
  const sums = []
  
  columns.forEach((column, index) => {
    if (index === 0) {
      sums[index] = '合计'
      return
    }
    
    if (column.property === 'quantity') {
      const values = data.map(item => Number(item[column.property]))
      sums[index] = values.reduce((prev, curr) => prev + curr, 0)
    } else if (column.property === 'amount') {
      const values = data.map(item => Number(item[column.property]))
      sums[index] = '¥' + values.reduce((prev, curr) => prev + curr, 0).toFixed(2)
    } else {
      sums[index] = ''
    }
  })
  
  return sums
}

onMounted(async () => {
  await loadRoutes()
  await loadSalespersons()
  await loadDailyReport()
  await loadTrendChart()
  await loadRankingChart()
  
  // 窗口大小改变时重绘图表
  window.addEventListener('resize', () => {
    trendChart?.resize()
    rankingChart?.resize()
  })
})
</script>

<style scoped lang="scss">
.reports-page {
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

  .charts-row {
    margin-bottom: 20px;
  }

  .report-card {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  }
}
</style>

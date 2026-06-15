import request from '../../utils/request'

/**
 * 获取概览统计数据
 * @param {string} period - 统计周期: today/week/month/custom
 */
export function getOverviewStats(period = 'today') {
  return request({
    url: '/api/dashboard/overview',
    method: 'get',
    params: { period }
  })
}

/**
 * 获取销售趋势数据
 * @param {number} days - 天数: 7/14/30
 */
export function getSalesTrend(days = 7) {
  return request({
    url: '/api/dashboard/chart/sales-trend',
    method: 'get',
    params: { days }
  })
}

/**
 * 获取商品销量排行
 * @param {number} limit - 返回数量
 * @param {string} period - 统计周期: week/month
 */
export function getProductRanking(limit = 10, period = 'week') {
  return request({
    url: '/api/dashboard/chart/product-ranking',
    method: 'get',
    params: { limit, period }
  })
}

/**
 * 获取客户分布统计
 */
export function getCustomerDistribution() {
  return request({
    url: '/api/dashboard/chart/customer-distribution',
    method: 'get'
  })
}

/**
 * 获取线路汇总统计
 * @param {string} date - 日期，格式: YYYY-MM-DD
 */
export function getRouteSummary(date) {
  return request({
    url: '/api/dashboard/route-summary',
    method: 'get',
    params: { date }
  })
}

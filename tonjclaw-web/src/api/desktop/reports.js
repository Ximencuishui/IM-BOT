import request from '../../utils/request'

// 获取日报表
export function getDailyReport(params) {
  return request({
    url: '/api/reports/daily',
    method: 'get',
    params
  })
}

// 导出Excel报表
export function exportReport(params) {
  return request({
    url: '/api/reports/export',
    method: 'get',
    params,
    responseType: 'blob'
  })
}

// 获取销售汇总
export function getSalesSummary(params) {
  return request({
    url: '/api/reports/sales-summary',
    method: 'get',
    params
  })
}

// 获取商品销量排行
export function getProductRanking(params) {
  return request({
    url: '/api/reports/product-sales',
    method: 'get',
    params
  })
}

// 获取客户活跃度
export function getCustomerActivity(params) {
  return request({
    url: '/api/reports/customer-activity',
    method: 'get',
    params
  })
}

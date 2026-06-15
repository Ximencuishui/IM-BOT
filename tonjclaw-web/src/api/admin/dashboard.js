import request from '../../utils/request'

export function getSystemStats() {
  return request({
    url: '/api/admin/stats',
    method: 'get'
  })
}

export function getLicenseStats() {
  return request({
    url: '/api/admin/license-stats',
    method: 'get'
  })
}

export function getSalesSummary(params) {
  return request({
    url: '/api/admin/reports/sales-summary',
    method: 'get',
    params
  })
}

export function getProductSales(params) {
  return request({
    url: '/api/admin/reports/product-sales',
    method: 'get',
    params
  })
}

export function getCustomerActivity(params) {
  return request({
    url: '/api/admin/reports/customer-activity',
    method: 'get',
    params
  })
}

export function getRecentActivities() {
  return request({
    url: '/api/admin/monitoring/recent-activities',
    method: 'get'
  })
}

export function getSalesTrend(params) {
  return request({
    url: '/api/admin/reports/sales-trend',
    method: 'get',
    params
  })
}

export function getUserGrowth(params) {
  return request({
    url: '/api/admin/reports/user-growth',
    method: 'get',
    params
  })
}

export function getSalesDetails(params) {
  return request({
    url: '/api/admin/reports/sales-details',
    method: 'get',
    params
  })
}
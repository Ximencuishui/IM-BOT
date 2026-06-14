import request from '@/utils/request'

// 获取订单列表
export function getOrders(params) {
  return request({
    url: '/api/admin/orders',
    method: 'get',
    params
  })
}

// 获取订单详情
export function getOrderDetail(orderId) {
  return request({
    url: `/api/admin/orders/${orderId}`,
    method: 'get'
  })
}

// 更新订单状态
export function updateOrderStatus(orderId, data) {
  return request({
    url: `/api/admin/orders/${orderId}/status`,
    method: 'put',
    data
  })
}

// 获取续费历史列表
export function getRenewalHistory(params) {
  return request({
    url: '/api/renewal-history/list',
    method: 'get',
    params
  })
}

// 获取续费统计
export function getRenewalStats() {
  return request({
    url: '/api/renewal-history/stats',
    method: 'get'
  })
}

// 获取指定授权码的续费历史
export function getLicenseRenewalHistory(licenseId) {
  return request({
    url: `/api/renewal-history/license/${licenseId}`,
    method: 'get'
  })
}

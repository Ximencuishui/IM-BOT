import request from '../../utils/request'

// 获取订单列表
export function getOrders(params) {
  return request({
    url: '/api/orders',
    method: 'get',
    params
  })
}

// 解析消息并创建订单
export function parseOrder(data) {
  return request({
    url: '/api/orders/parse',
    method: 'post',
    data
  })
}

// 创建订单
export function createOrder(data) {
  return request({
    url: '/api/orders',
    method: 'post',
    data
  })
}

// 获取订单详情
export function getOrderById(id) {
  return request({
    url: `/api/orders/${id}`,
    method: 'get'
  })
}

// 更新订单
export function updateOrder(id, data) {
  return request({
    url: `/api/orders/${id}`,
    method: 'put',
    data
  })
}

// 删除订单
export function deleteOrder(id) {
  return request({
    url: `/api/orders/${id}`,
    method: 'delete'
  })
}

// 获取今日订单统计
export function getTodayStats() {
  return request({
    url: '/api/orders/stats/today',
    method: 'get'
  })
}

// 批量确认订单
export function batchConfirmOrders(orderIds) {
  return request({
    url: '/api/orders/batch-confirm',
    method: 'post',
    data: { order_ids: orderIds }
  })
}

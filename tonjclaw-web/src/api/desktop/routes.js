import request from '../../utils/request'

// 获取所有线路列表
export function getRoutes(params = {}) {
  return request({
    url: '/api/routes',
    method: 'get',
    params
  })
}

// 创建新线路
export function createRoute(data) {
  return request({
    url: '/api/routes',
    method: 'post',
    data
  })
}

// 更新线路
export function updateRoute(routeId, data) {
  return request({
    url: `/api/routes/${routeId}`,
    method: 'put',
    data
  })
}

// 删除线路
export function deleteRoute(routeId) {
  return request({
    url: `/api/routes/${routeId}`,
    method: 'delete'
  })
}

// 更新线路产品自定义价格
export function updateRouteProductPrice(routeId, productId, customPrice) {
  return request({
    url: `/api/routes/${routeId}/products/${productId}/price`,
    method: 'put',
    data: { custom_price: customPrice }
  })
}

// 获取线路产品清单
export function getRouteProducts(routeId, params = {}) {
  return request({
    url: `/api/routes/${routeId}/products`,
    method: 'get',
    params
  })
}

// 为线路分配商品
export function assignProductsToRoute(routeId, productIds, customPrices = {}) {
  return request({
    url: `/api/routes/${routeId}/products`,
    method: 'post',
    data: {
      product_ids: productIds,
      custom_prices: customPrices
    }
  })
}

// 更新线路产品排序
export function updateRouteProductSort(routeId, productId, sortOrder) {
  return request({
    url: `/api/routes/${routeId}/products/${productId}`,
    method: 'put',
    data: { sort_order: sortOrder }
  })
}

// 从线路移除商品
export function removeProductFromRoute(routeId, productId) {
  return request({
    url: `/api/routes/${routeId}/products/${productId}`,
    method: 'delete'
  })
}

// 生成带序号的清单文本
export function generateNumberedList(routeId) {
  return request({
    url: `/api/routes/${routeId}/numbered-list`,
    method: 'get'
  })
}

import request from '../../utils/request'

// 获取商品列表
export function getProducts(params) {
  return request({
    url: '/api/products',
    method: 'get',
    params
  })
}

// 搜索商品
export function searchProducts(keyword) {
  return request({
    url: '/api/products/search',
    method: 'get',
    params: { keyword }
  })
}

// 获取商品详情
export function getProductById(id) {
  return request({
    url: `/api/products/${id}`,
    method: 'get'
  })
}

// 创建商品
export function createProduct(data) {
  return request({
    url: '/api/products',
    method: 'post',
    data
  })
}

// 更新商品
export function updateProduct(id, data) {
  return request({
    url: `/api/products/${id}`,
    method: 'put',
    data
  })
}

// 删除商品
export function deleteProduct(id) {
  return request({
    url: `/api/products/${id}`,
    method: 'delete'
  })
}

// 批量启用/禁用商品
export function batchUpdateStatus(ids, isActive) {
  return request({
    url: '/api/products/batch-status',
    method: 'put',
    data: { ids, is_active: isActive }
  })
}

// 获取字典选项（分类、单位等）
export function getDictOptions() {
  return request({
    url: '/api/products/dict/options',
    method: 'get'
  })
}

// 添加商品分类
export function addCategory(category) {
  return request({
    url: '/api/products/categories',
    method: 'post',
    data: { category }
  })
}

// 添加商品公共属性
export function addAttribute(attribute) {
  return request({
    url: '/api/products/attributes',
    method: 'post',
    data: { attribute }
  })
}

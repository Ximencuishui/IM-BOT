import request from '../../utils/request'

// 获取定价配置
export function getPricingConfig() {
  return request({
    url: '/api/admin/pricing',
    method: 'get'
  })
}

// 更新定价配置
export function updatePricingConfig(data) {
  return request({
    url: '/api/admin/pricing',
    method: 'post',
    data
  })
}

// 获取套餐列表
export function getPackages(params) {
  return request({
    url: '/api/admin/packages',
    method: 'get',
    params
  })
}

// 创建套餐
export function createPackage(data) {
  return request({
    url: '/api/admin/packages',
    method: 'post',
    data
  })
}

// 更新套餐
export function updatePackage(id, data) {
  return request({
    url: `/api/admin/packages/${id}`,
    method: 'put',
    data
  })
}

// 删除套餐
export function deletePackage(id) {
  return request({
    url: `/api/admin/packages/${id}`,
    method: 'delete'
  })
}

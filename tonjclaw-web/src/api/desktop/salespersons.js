import request from '../../utils/request'

// 获取销售人员列表
export function getSalespersons(params) {
  return request({
    url: '/api/salespersons',
    method: 'get',
    params
  })
}

// 获取销售人员详情
export function getSalespersonById(id) {
  return request({
    url: `/api/salespersons/${id}`,
    method: 'get'
  })
}

// 创建销售人员
export function createSalesperson(data) {
  return request({
    url: '/api/salespersons',
    method: 'post',
    data
  })
}

// 更新销售人员
export function updateSalesperson(id, data) {
  return request({
    url: `/api/salespersons/${id}`,
    method: 'put',
    data
  })
}

// 删除销售人员
export function deleteSalesperson(id) {
  return request({
    url: `/api/salespersons/${id}`,
    method: 'delete'
  })
}

// 获取统计数据
export function getSalespersonStats(params) {
  return request({
    url: '/api/salespersons/stats',
    method: 'get',
    params
  })
}

// 分配授权码
export function assignLicenses(salespersonId, licenseCodes) {
  return request({
    url: `/api/salespersons/${salespersonId}/licenses`,
    method: 'put',
    data: { license_codes: licenseCodes }
  })
}

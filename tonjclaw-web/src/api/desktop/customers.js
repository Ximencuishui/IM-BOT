import request from '../../utils/request'

// 获取客户列表
export function getCustomers(params) {
  return request({
    url: '/api/customers',
    method: 'get',
    params
  })
}

// 获取客户详情
export function getCustomerById(id) {
  return request({
    url: `/api/customers/${id}`,
    method: 'get'
  })
}

// 创建客户
export function createCustomer(data) {
  return request({
    url: '/api/customers',
    method: 'post',
    data
  })
}

// 更新客户
export function updateCustomer(id, data) {
  return request({
    url: `/api/customers/${id}`,
    method: 'put',
    data
  })
}

// 删除客户
export function deleteCustomer(id) {
  return request({
    url: `/api/customers/${id}`,
    method: 'delete'
  })
}

// 获取线路列表
export function getRoutes() {
  return request({
    url: '/api/customers/routes',
    method: 'get'
  })
}

// 导入客户
export function importCustomers(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: '/api/customers/import',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 导出客户
export function exportCustomers(params) {
  return request({
    url: '/api/customers/export',
    method: 'get',
    params,
    responseType: 'blob'
  })
}

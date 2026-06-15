import request from '../../utils/request'

// 获取所有授权码列表
export function getLicenses(params) {
  return request({
    url: '/api/admin/licenses',
    method: 'get',
    params: {
      page: params.page || 1,
      per_page: params.per_page || 20,
      license_code: params.license_code,
      user_email: params.user_email,
      status: params.status,
      type: params.type
    }
  })
}

// 生成新的授权码
export function generateLicense(data) {
  return request({
    url: '/api/license/generate',
    method: 'post',
    data
  })
}

// 撤销授权码
export function revokeLicense(id) {
  return request({
    url: `/api/admin/licenses/${id}/revoke`,
    method: 'post'
  })
}

// 单个授权码展期
export function extendLicense(id, data) {
  return request({
    url: `/api/admin/licenses/${id}/extend`,
    method: 'post',
    data
  })
}

// 批量展期授权码
export function batchExtendLicenses(data) {
  return request({
    url: '/api/admin/licenses/batch-extend',
    method: 'post',
    data
  })
}

// 获取授权统计信息
export function getLicenseStats() {
  return request({
    url: '/api/admin/license-stats',
    method: 'get'
  })
}

// 获取用户授权列表
export function getUserLicenses(userId, params) {
  return request({
    url: `/api/admin/users/${userId}/licenses`,
    method: 'get',
    params
  })
}
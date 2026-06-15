import request from '@/utils/request'

/**
 * 获取当前用户的授权码列表
 */
export function getLicenses() {
  return request({
    url: '/api/license/list',
    method: 'get'
  })
}

/**
 * 获取授权统计信息
 */
export function getLicenseStats() {
  return request({
    url: '/api/license/stats',
    method: 'get'
  })
}

/**
 * 激活授权码
 * @param {Object} data - { license_code, bound_to }
 */
export function activateLicense(data) {
  return request({
    url: '/api/license/activate',
    method: 'post',
    data
  })
}

/**
 * 撤销授权码
 * @param {number} licenseId - 授权码ID
 */
export function revokeLicense(licenseId) {
  return request({
    url: `/api/license/${licenseId}/revoke`,
    method: 'post'
  })
}

/**
 * 续期授权码
 * @param {number} licenseId - 授权码ID
 * @param {Object} data - { months: 续期月数 }
 */
export function extendLicense(licenseId, data) {
  return request({
    url: `/api/license/${licenseId}/extend`,
    method: 'post',
    data
  })
}

/**
 * 切换自动续费
 * @param {number} licenseId - 授权码ID
 * @param {boolean} autoRenew - 是否启用自动续费
 */
export function toggleAutoRenew(licenseId, autoRenew) {
  return request({
    url: `/api/license/${licenseId}/auto-renew`,
    method: 'post',
    data: { auto_renew: autoRenew }
  })
}

/**
 * 获取机器ID
 */
export function getMachineId() {
  return request({
    url: '/api/license/machine-id',
    method: 'get'
  })
}

import request from '../../utils/request'

export function getAllPermissions() {
  return request({
    url: '/api/admin/permissions',
    method: 'get'
  })
}

export function getUserPermissions(userId) {
  return request({
    url: `/api/admin/permissions/user/${userId}`,
    method: 'get'
  })
}

export function updateUserPermissions(userId, permissions) {
  return request({
    url: `/api/admin/permissions/user/${userId}`,
    method: 'put',
    data: { permissions }
  })
}

export function checkPermission(data) {
  return request({
    url: '/api/admin/permissions/check',
    method: 'post',
    data
  })
}

export function getAllRoles() {
  return request({
    url: '/api/admin/roles',
    method: 'get'
  })
}

export function getRolePermissions(roleName) {
  return request({
    url: `/api/admin/roles/${roleName}/permissions`,
    method: 'get'
  })
}
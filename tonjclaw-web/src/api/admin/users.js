import request from '../../utils/request'

// 获取所有用户
export function getUsers(params) {
  return request({
    url: '/api/admin/users',
    method: 'get',
    params
  })
}

// 创建用户
export function createUser(data) {
  return request({
    url: '/api/admin/users',
    method: 'post',
    data
  })
}

// 更新用户
export function updateUser(id, data) {
  return request({
    url: `/api/admin/users/${id}`,
    method: 'put',
    data
  })
}

// 删除用户
export function deleteUser(id) {
  return request({
    url: `/api/admin/users/${id}`,
    method: 'delete'
  })
}

// 重置用户密码
export function resetPassword(id, data) {
  return request({
    url: `/api/admin/users/${id}/reset-password`,
    method: 'post',
    data
  })
}

// 获取用户详细信息
export function getUserDetail(id) {
  return request({
    url: `/api/admin/users/${id}/detail`,
    method: 'get'
  })
}

import request from '../../utils/request'

export function getGroups(params = {}) {
  return request({
    url: '/api/desktop/groups',
    method: 'get',
    params: { sync: params.sync !== false ? '1' : '0' }
  })
}

export function getHookChatrooms() {
  return request({
    url: '/api/desktop/groups/hook/chatrooms',
    method: 'get'
  })
}

export function bindGroup(data) {
  return request({
    url: '/api/desktop/groups/bind',
    method: 'post',
    data
  })
}

export function redeemGroup(data) {
  return request({
    url: '/api/desktop/groups/redeem',
    method: 'post',
    data
  })
}

export function unbindGroup(wx_group_id) {
  return request({
    url: '/api/desktop/groups/unbind',
    method: 'post',
    data: { wx_group_id }
  })
}

export function batchRedeemGroups(wx_group_ids, codes) {
  return request({
    url: '/api/desktop/groups/batch-redeem',
    method: 'post',
    data: { wx_group_ids, codes }
  })
}

export function linkGroupCustomer(wx_group_id, customer_id) {
  return request({
    url: '/api/desktop/groups/link-customer',
    method: 'post',
    data: { wx_group_id, customer_id }
  })
}

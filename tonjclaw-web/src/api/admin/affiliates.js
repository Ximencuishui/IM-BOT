import request from '@/utils/request'

// 获取推广员列表
export function getPromoters(params) {
  return request({
    url: '/api/admin/affiliates/promoters',
    method: 'get',
    params
  })
}

// 创建推广员
export function createPromoter(data) {
  return request({
    url: '/api/admin/affiliates/promoters',
    method: 'post',
    data
  })
}

// 更新推广员
export function updatePromoter(promoterId, data) {
  return request({
    url: `/api/admin/affiliates/promoters/${promoterId}`,
    method: 'put',
    data
  })
}

// 删除推广员
export function deletePromoter(promoterId) {
  return request({
    url: `/api/admin/affiliates/promoters/${promoterId}`,
    method: 'delete'
  })
}

// 重新生成推广链接
export function regeneratePromoLink(promoterId) {
  return request({
    url: `/api/admin/affiliates/promoters/${promoterId}/regenerate-link`,
    method: 'post'
  })
}

// 获取推广统计
export function getAffiliateStats() {
  return request({
    url: '/api/admin/affiliates/stats',
    method: 'get'
  })
}

import request from '@/utils/request'

// 获取审计日志列表
export function getAuditLogs(params) {
  return request({
    url: '/api/admin/audit-logs',
    method: 'get',
    params
  })
}

// 获取审计统计
export function getAuditStats() {
  return request({
    url: '/api/admin/audit-logs/stats',
    method: 'get'
  })
}

// 导出审计日志
export function exportAuditLogs(data) {
  return request({
    url: '/api/admin/audit-logs/export',
    method: 'post',
    data
  })
}

// 清理旧日志
export function cleanupOldLogs(days) {
  return request({
    url: '/api/admin/audit-logs/cleanup',
    method: 'post',
    data: { days }
  })
}

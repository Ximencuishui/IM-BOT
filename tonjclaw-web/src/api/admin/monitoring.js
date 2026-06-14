import request from '@/utils/request'

// 获取系统状态
export function getSystemStatus() {
  return request({
    url: '/api/admin/monitoring/system-status',
    method: 'get'
  })
}

// 获取应用状态
export function getAppStatus() {
  return request({
    url: '/api/admin/monitoring/app-status',
    method: 'get'
  })
}

// 获取数据库状态
export function getDatabaseStatus() {
  return request({
    url: '/api/admin/monitoring/database-status',
    method: 'get'
  })
}

// 获取最近活动
export function getRecentActivities() {
  return request({
    url: '/api/admin/monitoring/recent-activities',
    method: 'get'
  })
}

// 获取健康摘要
export function getHealthSummary() {
  return request({
    url: '/api/admin/monitoring/health-summary',
    method: 'get'
  })
}

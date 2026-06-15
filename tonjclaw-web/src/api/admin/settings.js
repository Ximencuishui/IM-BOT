import request from '@/utils/request'

// 获取邮件配置
export function getEmailConfig() {
  return request({
    url: '/api/admin/system/email-config',
    method: 'get'
  })
}

// 保存邮件配置
export function saveEmailConfig(data) {
  return request({
    url: '/api/admin/system/email-config',
    method: 'post',
    data
  })
}

// 测试邮件发送
export function testEmailSend(data) {
  return request({
    url: '/api/admin/system/test-email',
    method: 'post',
    data
  })
}

// 获取支付宝配置
export function getAlipayConfig() {
  return request({
    url: '/api/admin/system/alipay-config',
    method: 'get'
  })
}

// 保存支付宝配置
export function saveAlipayConfig(data) {
  return request({
    url: '/api/admin/system/alipay-config',
    method: 'post',
    data
  })
}

// 获取微信支付配置
export function getWechatConfig() {
  return request({
    url: '/api/admin/system/wechat-config',
    method: 'get'
  })
}

// 保存微信支付配置
export function saveWechatConfig(data) {
  return request({
    url: '/api/admin/system/wechat-config',
    method: 'post',
    data
  })
}

// 获取系统参数
export function getSystemParams() {
  return request({
    url: '/api/admin/system/params',
    method: 'get'
  })
}

// 保存系统参数
export function saveSystemParams(data) {
  return request({
    url: '/api/admin/system/params',
    method: 'post',
    data
  })
}

// 获取 AI 解析配置
export function getAiParserConfig() {
  return request({
    url: '/api/admin/system/ai-parser-config',
    method: 'get'
  })
}

// 保存 AI 解析配置
export function saveAiParserConfig(data) {
  return request({
    url: '/api/admin/system/ai-parser-config',
    method: 'post',
    data
  })
}

// 获取通知模板列表
export function getNotificationTemplates() {
  return request({
    url: '/api/admin/system/notification-templates',
    method: 'get'
  })
}

// 创建通知模板
export function createNotificationTemplate(data) {
  return request({
    url: '/api/admin/system/notification-templates',
    method: 'post',
    data
  })
}

// 更新通知模板
export function updateNotificationTemplate(id, data) {
  return request({
    url: `/api/admin/system/notification-templates/${id}`,
    method: 'put',
    data
  })
}

// 删除通知模板
export function deleteNotificationTemplate(id) {
  return request({
    url: `/api/admin/system/notification-templates/${id}`,
    method: 'delete'
  })
}

// 预览通知模板
export function previewNotificationTemplate(data) {
  return request({
    url: '/api/admin/system/notification-templates/preview',
    method: 'post',
    data
  })
}

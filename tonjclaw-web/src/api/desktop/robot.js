import request from '../../utils/request'

// 获取机器人配置列表
export function getRobotConfigs() {
  return request({
    url: '/api/robot/configs',
    method: 'get'
  })
}

// 获取默认配置
export function getDefaultConfig() {
  return request({
    url: '/api/robot/configs/default',
    method: 'get'
  })
}

// 创建机器人配置
export function createRobotConfig(data) {
  return request({
    url: '/api/robot/configs',
    method: 'post',
    data
  })
}

// 更新机器人配置
export function updateRobotConfig(id, data) {
  return request({
    url: `/api/robot/configs/${id}`,
    method: 'put',
    data
  })
}

// 获取回复规则列表
export function getReplyRules(configId) {
  return request({
    url: `/api/robot/configs/${configId}/reply-rules`,
    method: 'get'
  })
}

// 创建回复规则
export function createReplyRule(data) {
  return request({
    url: '/api/robot/reply-rules',
    method: 'post',
    data
  })
}

// 更新回复规则
export function updateReplyRule(id, data) {
  return request({
    url: `/api/robot/reply-rules/${id}`,
    method: 'put',
    data
  })
}

// 删除回复规则
export function deleteReplyRule(id) {
  return request({
    url: `/api/robot/reply-rules/${id}`,
    method: 'delete'
  })
}

// 测试回复规则
export function testReplyRule(ruleId, testMessage) {
  return request({
    url: `/api/robot/reply-rules/${ruleId}/test`,
    method: 'post',
    data: { message: testMessage }
  })
}

// 获取机器人状态
export function getRobotStatus() {
  return request({
    url: '/api/robot/status',
    method: 'get'
  })
}

// 保存智能指令配置
export function saveCommandConfig(data) {
  return request({
    url: '/api/robot/command-config',
    method: 'post',
    data
  })
}

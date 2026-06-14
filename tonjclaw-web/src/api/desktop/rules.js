import request from '../../utils/request'

// 获取解析规则列表
export function getParseRules(params) {
  return request({
    url: '/api/rules/parse',
    method: 'get',
    params
  })
}

// 创建解析规则
export function createParseRule(data) {
  return request({
    url: '/api/rules/parse',
    method: 'post',
    data
  })
}

// 更新解析规则
export function updateParseRule(id, data) {
  return request({
    url: `/api/rules/parse/${id}`,
    method: 'put',
    data
  })
}

// 删除解析规则
export function deleteParseRule(id) {
  return request({
    url: `/api/rules/parse/${id}`,
    method: 'delete'
  })
}

// 测试解析规则
export function testParseRule(ruleId, testText) {
  return request({
    url: `/api/rules/parse/${ruleId}/test`,
    method: 'post',
    data: { text: testText }
  })
}

// 获取统计规则列表
export function getStatRules(params) {
  return request({
    url: '/api/rules/stat',
    method: 'get',
    params
  })
}

// 创建统计规则
export function createStatRule(data) {
  return request({
    url: '/api/rules/stat',
    method: 'post',
    data
  })
}

// 更新统计规则
export function updateStatRule(id, data) {
  return request({
    url: `/api/rules/stat/${id}`,
    method: 'put',
    data
  })
}

// 删除统计规则
export function deleteStatRule(id) {
  return request({
    url: `/api/rules/stat/${id}`,
    method: 'delete'
  })
}

// 导入规则
export function importRules(file, options = {}) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('format', options.format || 'csv')
  formData.append('conflict_strategy', options.conflictStrategy || 'skip')
  return request({
    url: '/api/rules/import',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 获取规则模板列表
export function getRuleTemplates() {
  return request({
    url: '/api/rules/templates',
    method: 'get'
  })
}

// 应用规则模板
export function applyTemplate(templateId) {
  return request({
    url: `/api/rules/templates/${templateId}/apply`,
    method: 'post'
  })
}

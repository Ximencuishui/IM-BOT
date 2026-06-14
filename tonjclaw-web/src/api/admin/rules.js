import request from '@/utils/request'

// 获取规则模板列表
export function getRuleTemplates(params) {
  return request({
    url: '/api/admin/rules/templates',
    method: 'get',
    params
  })
}

// 创建规则模板
export function createRuleTemplate(data) {
  return request({
    url: '/api/admin/rules/templates',
    method: 'post',
    data
  })
}

// 更新规则模板
export function updateRuleTemplate(id, data) {
  return request({
    url: `/api/admin/rules/templates/${id}`,
    method: 'put',
    data
  })
}

// 删除规则模板
export function deleteRuleTemplate(id) {
  return request({
    url: `/api/admin/rules/templates/${id}`,
    method: 'delete'
  })
}

// 获取规则导入任务预览
export function getImportPreview(taskId) {
  return request({
    url: `/api/rules/import/preview/${taskId}`,
    method: 'get'
  })
}

// 确认规则导入
export function confirmImport(taskId) {
  return request({
    url: `/api/rules/import/confirm/${taskId}`,
    method: 'put'
  })
}

// 取消规则导入
export function cancelImport(taskId) {
  return request({
    url: `/api/rules/import/cancel/${taskId}`,
    method: 'post'
  })
}

// 导出规则
export function exportRules(params) {
  return request({
    url: '/api/rules/export',
    method: 'get',
    params,
    responseType: 'blob'
  })
}

/** 从 axios 错误中提取后端返回的可读说明 */
export function extractApiError(err, fallback = '操作失败') {
  const data = err?.response?.data
  if (typeof data === 'string' && data.trim()) return data.trim()
  if (data && typeof data === 'object') {
    if (data.error) return String(data.error)
    if (data.message) return String(data.message)
    if (data.stderr) return String(data.stderr)
  }
  return err?.message || fallback
}

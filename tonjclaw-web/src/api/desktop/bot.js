import request from '../../utils/request'

export function setBotInbound(enabled) {
  return request({
    url: '/api/desktop/bot/inbound',
    method: 'post',
    data: { enabled }
  })
}

export function getBotWorkLogs(limit = 80) {
  return request({
    url: '/api/desktop/bot/work-logs',
    method: 'get',
    params: { limit }
  })
}

export function getWechatExePath() {
  return request({ url: '/api/desktop/bot/wechat-exe-path', method: 'get' })
}

export function saveWechatExePath(path) {
  return request({
    url: '/api/desktop/bot/wechat-exe-path',
    method: 'post',
    data: { path }
  })
}

/** 默认冷注入（先关微信）；hot=true 时不关微信；可传 wechat_exe_path */
export function runBotWechatInject(hot = false, extra = {}) {
  return request({
    url: '/api/desktop/bot/wechat-inject',
    method: 'post',
    params: hot ? { hot: '1' } : {},
    data: extra.wechat_exe_path ? { wechat_exe_path: extra.wechat_exe_path } : {},
    timeout: 120000
  })
}

export function getLicenseStatus() {
  return request({ url: '/api/desktop/license-status', method: 'get', timeout: 15000 })
}

export function getBotStatus() {
  return request({ url: '/api/desktop/bot/status', method: 'get', timeout: 45000 })
}

export function redeemRobotCard(data) {
  return request({
    url: '/api/desktop/robot-redeem',
    method: 'post',
    data
  })
}

export function getRobotConfig() {
  return request({ url: '/api/desktop/robot-config', method: 'get' })
}

export function parseTest(content) {
  return request({
    url: '/api/desktop/debug/parse-test',
    method: 'post',
    data: { content }
  })
}

export function getOpsBackupStatus() {
  return request({ url: '/api/desktop/ops/backup', method: 'get' })
}

export function runOpsBackup() {
  return request({ url: '/api/desktop/ops/backup', method: 'post' })
}

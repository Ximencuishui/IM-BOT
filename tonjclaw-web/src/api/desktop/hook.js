import request from '../../utils/request'

export function getTrayHealth() {
  return request({
    url: '/api/health/tray',
    method: 'get'
  }).catch(() =>
    request({
      url: '/api/robot/hook-health',
      method: 'get'
    })
  )
}

export function runWechatInject(hot = false, extra = {}) {
  const params = hot ? { hot: '1' } : {}
  const data = extra.wechat_exe_path ? { wechat_exe_path: extra.wechat_exe_path } : {}
  const opts = { method: 'post', params, data, timeout: 120000 }
  return request({ url: '/api/bot/wechat-inject', ...opts }).catch(() =>
    request({ url: '/api/robot/wechat-inject', ...opts })
  )
}

export function getHookInjectConfig() {
  return request({
    url: '/api/hook/inject-config',
    method: 'get'
  })
}

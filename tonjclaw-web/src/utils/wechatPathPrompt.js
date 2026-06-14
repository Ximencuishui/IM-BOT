import { ElMessage, ElMessageBox } from 'element-plus'
import { getWechatExePath, saveWechatExePath } from '../api/desktop/bot'

const LS_KEY = 'tonjclaw_wechat_exe_path'

export function getLocalWechatExePath() {
  try {
    return localStorage.getItem(LS_KEY) || ''
  } catch {
    return ''
  }
}

export function setLocalWechatExePath(path) {
  try {
    if (path) localStorage.setItem(LS_KEY, path)
    else localStorage.removeItem(LS_KEY)
  } catch {
    /* ignore */
  }
}

function isNeedWechatPath(result) {
  if (!result) return false
  if (result.need_wechat_path) return true
  const err = String(result.error || '')
  return /未找到.*微信|Weixin\.exe|WECHAT_EXE_PATH/i.test(err)
}

/**
 * 未找到微信时弹窗让用户输入路径，保存后返回路径；取消则返回 null。
 */
export async function promptWechatExePath(initial = '') {
  let defaultPath = initial || getLocalWechatExePath()
  try {
    const info = await getWechatExePath()
    defaultPath = defaultPath || info?.saved_path || info?.detected_path || info?.path || ''
  } catch {
    /* ignore */
  }

  try {
    const { value } = await ElMessageBox.prompt(
      '系统未能自动找到微信主程序（Weixin.exe）。\n\n请粘贴完整路径，例如：\nD:\\Weixin\\Weixin.exe\n或\nC:\\Program Files\\Tencent\\Weixin\\Weixin.exe',
      '指定微信安装路径',
      {
        confirmButtonText: '保存并继续',
        cancelButtonText: '取消',
        inputValue: defaultPath,
        inputPlaceholder: '例如 D:\\Weixin\\Weixin.exe',
        type: 'warning',
        inputValidator: (val) => {
          const v = String(val || '').trim()
          if (!v) return '请输入路径'
          if (!/\\.(exe)$/i.test(v)) return '请选择 .exe 文件'
          return true
        }
      }
    )
    const path = String(value || '').trim()
    const saved = await saveWechatExePath(path)
    const finalPath = saved?.path || path
    setLocalWechatExePath(finalPath)
    ElMessage.success('微信路径已保存')
    return finalPath
  } catch {
    return null
  }
}

/**
 * 执行注入；若未找到微信则弹窗引导输入路径并自动重试一次。
 */
export async function runWechatInjectWithPathPrompt(injectFn, hot = false) {
  let exePath = getLocalWechatExePath()
  try {
    const info = await getWechatExePath()
    exePath = exePath || info?.saved_path || info?.path || ''
  } catch {
    /* ignore */
  }

  const doInject = (path) =>
    injectFn(hot, path ? { wechat_exe_path: path } : {})

  let result = await doInject(exePath)
  if (result?.ok || !isNeedWechatPath(result)) {
    return result
  }

  const chosen = await promptWechatExePath(exePath)
  if (!chosen) {
    return { ...result, cancelled: true }
  }
  return doInject(chosen)
}

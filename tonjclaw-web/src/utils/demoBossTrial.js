import { ElMessageBox } from 'element-plus'

export const DEMO_TRIAL_DIALOG_KEY = 'tonjclaw_demo_trial_dialog_shown'
export const DEMO_LICENSE_CACHE_KEY = 'tonjclaw_demo_license'

export function isDemoBossUser(userInfo) {
  if (!userInfo) return false
  const email = String(userInfo.email || '').toLowerCase()
  const username = String(userInfo.username || '').toUpperCase()
  return email === 'boss@demo.local' || username === 'BOSS'
}

export function cacheDemoLicense(demoLicense) {
  if (!demoLicense) return
  try {
    sessionStorage.setItem(DEMO_LICENSE_CACHE_KEY, JSON.stringify(demoLicense))
  } catch {
    /* ignore */
  }
}

export function readCachedDemoLicense() {
  try {
    const raw = sessionStorage.getItem(DEMO_LICENSE_CACHE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function buildDemoTrialHtml({ expireDisplay, maxGroups = 3, days = 1, boundGroups, remainingGroups } = {}) {
  const expire = expireDisplay || '—'
  const bound =
    boundGroups != null ? `已绑定 ${boundGroups} 个` : ''
  const remain =
    remainingGroups != null ? `，还可绑定 ${remainingGroups} 个` : ''
  return `
    <div class="demo-trial-dialog">
      <p><strong>BOSS 演示账号 · 免费测试</strong></p>
      <ul>
        <li>测试周期：<strong>${days} 天</strong>（到期日：<strong>${expire}</strong>）</li>
        <li>可绑定微信群：<strong>最多 ${maxGroups} 个</strong>${bound}${remain}</li>
        <li>主程序与群服务<strong>无需卡密</strong>，登录自动开通</li>
      </ul>
      <p class="demo-trial-hint">建议：先在「群管理」绑定要统计的群（不超过 ${maxGroups} 个），再在「机器人运行」完成 Hook 注入。到期后请使用正式卡密续费。</p>
    </div>
  `
}

export async function showDemoBossTrialDialog(options = {}) {
  const html = buildDemoTrialHtml(options)
  await ElMessageBox.alert(html, '免费测试说明', {
    confirmButtonText: '我知道了',
    type: 'info',
    dangerouslyUseHTMLString: true,
    customClass: 'demo-trial-message-box'
  })
}

/** 每个浏览器会话仅弹一次（BOSS 进入桌面端时） */
export async function maybeShowDemoBossTrialDialog(userInfo, demoLicense) {
  if (!isDemoBossUser(userInfo)) return
  if (sessionStorage.getItem(DEMO_TRIAL_DIALOG_KEY)) return
  sessionStorage.setItem(DEMO_TRIAL_DIALOG_KEY, '1')
  const lic = demoLicense || readCachedDemoLicense() || {}
  await showDemoBossTrialDialog({
    expireDisplay: lic.expire_display,
    maxGroups: lic.max_groups ?? userInfo?.max_groups ?? 3,
    days: lic.days ?? 1,
    boundGroups: lic.bound_groups,
    remainingGroups: lic.remaining_groups
  })
}

<template>
  <header class="desktop-hook-bar">
    <div class="desktop-hook-wx">
      <div class="desktop-hook-avatar">
        {{ avatarLetter }}
      </div>
      <div class="desktop-hook-text">
        <strong>{{ profile.nickname || profile.wxid || '微信 Hook' }}</strong>
        <span v-if="profile.wxid" class="desktop-hook-wxid">
          {{ profile.wxid }}
          <el-button link type="primary" size="small" @click="copyWxid">复制</el-button>
        </span>
      </div>
    </div>

    <div class="desktop-hook-capsules" role="status">
      <button
        type="button"
        class="status-capsule"
        :class="`status-capsule--${wechatCapsule.level}`"
        :disabled="injectBusy"
        @click="onWechatCapsuleClick"
      >
        <span class="status-dot" />
        {{ wechatCapsule.text }}
      </button>
      <span class="status-capsule" :class="`status-capsule--${inboundCapsule.level}`">
        <span class="status-dot" />
        {{ inboundCapsule.text }}
      </span>
      <el-button
        size="small"
        :loading="loading"
        @click="refresh"
      >
        刷新状态
      </el-button>
      <el-button
        size="small"
        type="primary"
        :loading="injectBusy"
        @click="onManualInject"
      >
        注入 Hook
      </el-button>
    </div>
  </header>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getTrayHealth, runWechatInject } from '../../api/desktop/hook'
import { extractApiError } from '../../utils/apiError'
import { runWechatInjectWithPathPrompt } from '../../utils/wechatPathPrompt'
import { runBotWechatInject } from '../../api/desktop/bot'
import { getLicenseStatus } from '../../api/desktop/bot'

const router = useRouter()
const tray = ref({})
const licenseStatus = ref({ robot_valid: false, expire_display: '—' })
const loading = ref(false)
const injectBusy = ref(false)
let pollId = null

const profile = computed(() => tray.value?.hook_profile || {})

const avatarLetter = computed(() => {
  const n = profile.value.nickname || profile.value.wxid || 'W'
  return String(n).charAt(0).toUpperCase()
})

function hookOperational(t) {
  return Boolean(t.hook_ready || t.hook_has_wxid || t.hook_stored_wxid)
}

const wechatCapsule = computed(() => {
  const t = tray.value || {}
  if (!t.wechat_process_running) {
    return { level: 'warn', text: '微信未运行' }
  }
  if (injectBusy.value) {
    return { level: 'warn', text: '正在注入 Hook…' }
  }
  if (!hookOperational(t)) {
    if (t.hook_wechat_login_required) {
      return { level: 'warn', text: '请完成微信登录' }
    }
    return { level: 'warn', text: 'Hook 未就绪（点击注入）' }
  }
  return { level: 'ok', text: '微信 · Hook 正常' }
})

const inboundCapsule = computed(() => {
  const t = tray.value || {}
  if (t.inbound_enabled === false) {
    return { level: 'warn', text: '入站已暂停' }
  }
  const n = Number(t.inbound_recv_count || 0)
  return {
    level: 'ok',
    text: n > 0 ? `入站运行中 · ${n} 条` : '入站运行中'
  }
})

function goRenewal() {
  router.push({ path: '/desktop/robot', query: { tab: 'renewal' } })
}

function goGroupRenew() {
  router.push({ path: '/desktop/groups', query: { tab: 'renew' } })
}

async function refresh() {
  loading.value = true
  try {
    const [t, lic] = await Promise.all([
      getTrayHealth().catch(() => ({})),
      getLicenseStatus().catch(() => ({}))
    ])
    tray.value = t || {}
    licenseStatus.value = {
      robot_valid: !!(lic?.robot_valid ?? t?.robot_valid),
      expire_display: lic?.expire_display || t?.expire_display || '—',
      demo_auto_license: !!(lic?.demo_auto_license ?? t?.demo_auto_license)
    }
  } catch (e) {
    tray.value = {}
    ElMessage.error(e?.message || '无法读取 Hook 状态')
  } finally {
    loading.value = false
  }
}

async function onManualInject() {
  if (injectBusy.value) return
  injectBusy.value = true
  try {
    const d = await runWechatInjectWithPathPrompt(
      (hot, extra) => runBotWechatInject(hot, extra).catch(() => runWechatInject(hot, extra)),
      false
    )
    if (d?.cancelled) return
    if (d?.ok) {
      ElMessage.success('微信 Hook 注入完成')
      await refresh()
    } else {
      ElMessage.error(d?.error || '注入失败')
    }
  } catch (e) {
    ElMessage.error(extractApiError(e, '注入失败'))
  } finally {
    injectBusy.value = false
  }
}

function onWechatCapsuleClick() {
  if (wechatCapsule.value.level === 'ok' || injectBusy.value) return
  onManualInject()
}

function copyWxid() {
  const wxid = profile.value.wxid
  if (!wxid || !navigator.clipboard) return
  navigator.clipboard.writeText(String(wxid))
  ElMessage.success('已复制 wxid')
}

onMounted(() => {
  refresh()
  pollId = setInterval(refresh, 12000)
})

onUnmounted(() => {
  if (pollId) clearInterval(pollId)
})

defineExpose({ refresh })
</script>

<style scoped lang="scss">
.desktop-hook-bar {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
  padding: 0.65rem 1rem;
  background: #fff;
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  box-shadow: 0 1px 0 rgba(15, 23, 42, 0.04);
}

.desktop-hook-wx {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
  flex: 1;
}

.desktop-hook-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #5b4ae8, #0d9488);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
}

.desktop-hook-text {
  display: flex;
  flex-direction: column;
  min-width: 0;

  strong {
    font-size: 14px;
    color: #1e293b;
  }
}

.desktop-hook-wxid {
  font-size: 12px;
  color: #64748b;
}

.desktop-hook-capsules {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.status-capsule {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.25rem 0.65rem;
  border-radius: 999px;
  font-size: 12px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #475569;
  font-family: inherit;
}

button.status-capsule {
  cursor: pointer;

  &:disabled {
    opacity: 0.7;
    cursor: wait;
  }
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.status-capsule--ok {
  border-color: rgba(34, 197, 94, 0.35);
  background: rgba(34, 197, 94, 0.08);
  color: #15803d;
}

.status-capsule--warn {
  border-color: rgba(234, 179, 8, 0.4);
  background: rgba(234, 179, 8, 0.1);
  color: #a16207;
}

.status-capsule--danger {
  border-color: rgba(239, 68, 68, 0.35);
  background: rgba(239, 68, 68, 0.08);
  color: #b91c1c;
}
</style>

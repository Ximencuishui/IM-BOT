<template>
  <div class="robot-page desktop-card">
    <section class="bot-tab-strip">
      <button
        v-for="t in tabs"
        :key="t.id"
        type="button"
        class="bot-tab"
        :class="{ 'bot-tab--active': subPage === t.id }"
        @click="setSubPage(t.id)"
      >
        <span class="bot-tab-icon" :style="{ '--accent': t.color }">{{ t.icon }}</span>
        <span class="bot-tab-title">{{ t.title }}</span>
        <span class="bot-tab-desc">{{ t.desc }}</span>
      </button>
    </section>

    <!-- 运行状况 -->
    <template v-if="subPage === 'status'">
      <el-alert
        v-if="licenseStatus.demo_auto_license && licenseStatus.robot_valid"
        type="success"
        show-icon
        :closable="false"
        title="BOSS 演示账号已自动开通"
        :description="`免费测试 1 天、最多 3 群，主程序可用至 ${licenseStatus.expire_display || '—'}（无需卡密）`"
        style="margin-bottom: 16px"
      />
      <el-alert
        v-else-if="!licenseStatus.robot_valid"
        type="warning"
        show-icon
        :closable="false"
        title="主程序授权无效或已过期"
        description="请切换到「主程序续费」粘贴 SimBot 管理平台下发的卡密；入站处理与注入需有效授权。"
        style="margin-bottom: 16px"
      />

      <el-card shadow="never" class="panel-card">
        <template #header>机器人启动与运行</template>
        <el-row :gutter="24">
          <el-col :span="12">
            <h4>连接微信</h4>
            <p class="muted">
              默认<strong>冷注入</strong>：先关闭已运行的微信，再查找并注入 Hook（成功率更高）。需 Windows + hk 套件。
              若提示找不到微信，请在项目 <code>.env</code> 设置 <code>WECHAT_EXE_PATH</code> 为 Weixin.exe 完整路径。
            </p>
            <el-button type="primary" :loading="injectBusy" @click="handleInject()">
              {{ injectBusy ? '正在冷注入…' : '查找微信并注入' }}
            </el-button>
            <el-button
              link
              type="info"
              :disabled="injectBusy"
              style="margin-left: 8px"
              @click="handleInject(true)"
            >
              热注入（不关微信）
            </el-button>
            <pre v-if="injectLog" class="inject-log">{{ injectLog }}</pre>
          </el-col>
          <el-col :span="12">
            <h4>处理入站消息</h4>
            <p class="muted">暂停后不再解析订单；微信进程不受影响。</p>
            <div class="inbound-row">
              <el-button
                :type="botStatus.inbound_enabled ? 'warning' : 'success'"
                circle
                size="large"
                :disabled="!licenseStatus.robot_valid"
                @click="toggleInbound"
              >
                <el-icon v-if="botStatus.inbound_enabled"><VideoPause /></el-icon>
                <el-icon v-else><VideoPlay /></el-icon>
              </el-button>
              <div class="inbound-meta">
                <div>启动时间：{{ startedLabel }}</div>
                <div>运行时长：{{ durationLabel }}</div>
                <div v-if="licenseStatus.expire_display">
                  授权到期：{{ licenseStatus.expire_display }}
                </div>
              </div>
            </div>
          </el-col>
        </el-row>
      </el-card>

      <el-card shadow="never" class="panel-card" style="margin-top: 16px">
        <template #header>
          <div class="card-header">
            <span>工作日志</span>
            <el-button size="small" @click="loadWorkLogs">刷新</el-button>
          </div>
        </template>
        <el-table :data="workLogs" size="small" max-height="320" empty-text="暂无日志">
          <el-table-column prop="created_at" label="时间" width="170" />
          <el-table-column prop="level" label="级别" width="80" />
          <el-table-column prop="message" label="内容" show-overflow-tooltip />
        </el-table>
      </el-card>
    </template>

    <!-- 调试工具 -->
    <template v-if="subPage === 'tool'">
      <el-card shadow="never" class="panel-card">
        <template #header>订单解析试算</template>
        <el-input
          v-model="parseText"
          type="textarea"
          :rows="4"
          placeholder="输入群消息文本，例如：白菜10斤 鸡蛋5斤"
        />
        <el-button type="primary" style="margin-top: 12px" :loading="parseBusy" @click="runParseTest">
          试算
        </el-button>
        <pre v-if="parseResult" class="parse-result">{{ parseResult }}</pre>
      </el-card>
    </template>

    <!-- 主程序续费 -->
    <template v-if="subPage === 'renewal'">
      <el-card shadow="never" class="panel-card">
        <template #header>机器人主程序续费（SimBot 管理平台）</template>
        <el-alert
          v-if="licenseStatus.demo_auto_license"
          type="success"
          :closable="false"
          show-icon
          style="margin-bottom: 16px"
        >
          BOSS 演示账号：1 天免费测试、最多 3 个群（到期 {{ licenseStatus.expire_display || '—' }}），无需粘贴卡密。
        </el-alert>
        <el-alert
          v-else
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 16px"
        >
          请粘贴销售/管理平台下发的 RSA 卡密或 32 位短码；核销逻辑与 sim-bot-node 一致。可配置
          <code>SIMBOT_PLATFORM_URL</code> 走平台 API，或本地 <code>ACTIVATION_PUBLIC_KEY</code> 验签。
        </el-alert>

        <el-descriptions :column="2" border style="margin-bottom: 16px">
          <el-descriptions-item label="当前 wxid">
            {{ hookWxid || '未识别（请先注入并完成微信登录）' }}
          </el-descriptions-item>
          <el-descriptions-item label="授权状态">
            <el-tag :type="licenseStatus.robot_valid ? 'success' : 'danger'">
              {{ licenseStatus.robot_valid ? '有效' : '无效/未激活' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="到期日">
            {{ licenseStatus.expire_display || '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="完整性">
            <el-tag :type="licenseStatus.integrity_ok !== false ? 'success' : 'danger'">
              {{ licenseStatus.integrity_ok !== false ? '正常' : '异常' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <el-form label-width="100px">
          <el-form-item label="机器 wxid">
            <el-input v-model="renewWxid" placeholder="自动填充，可手动修正" />
          </el-form-item>
          <el-form-item label="卡密密文" required>
            <el-input
              v-model="renewCipher"
              type="textarea"
              :rows="5"
              placeholder="粘贴 SimBot 管理平台 RSA 卡密或 32 位短码"
            />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="renewBusy" @click="submitRenew">
              卡密激活
            </el-button>
          </el-form-item>
        </el-form>
        <p v-if="renewMsg" :class="renewOk ? 'ok-text' : 'err-text'">{{ renewMsg }}</p>
      </el-card>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { VideoPause, VideoPlay } from '@element-plus/icons-vue'
import {
  getBotStatus,
  setBotInbound,
  getBotWorkLogs,
  runBotWechatInject,
  getLicenseStatus,
  redeemRobotCard,
  parseTest
} from '../../../api/desktop/bot'
import { getTrayHealth } from '../../../api/desktop/hook'
import { extractApiError } from '../../../utils/apiError'
import { runWechatInjectWithPathPrompt } from '../../../utils/wechatPathPrompt'

const route = useRoute()
const router = useRouter()

const tabs = [
  { id: 'status', title: '运行状况', desc: '注入、入站、工作日志', icon: '◉', color: '#f97316' },
  { id: 'tool', title: '调试工具', desc: '订单解析试算', icon: '⚒', color: '#0d9488' },
  { id: 'renewal', title: '主程序续费', desc: 'SimBot 管理平台卡密', icon: '🔑', color: '#5b4ae8' }
]

const subPage = ref('status')
const botStatus = ref({ inbound_enabled: false, started_at: null })
const licenseStatus = ref({ robot_valid: false, expire_display: '—', integrity_ok: true })
const workLogs = ref([])
const injectBusy = ref(false)
const injectLog = ref('')
const parseText = ref('')
const parseBusy = ref(false)
const parseResult = ref('')
const renewWxid = ref('')
const renewCipher = ref('')
const renewBusy = ref(false)
const renewMsg = ref('')
const renewOk = ref(true)
const hookWxid = ref('')
const runtimeTick = ref(Date.now())

let pollId = null
let clockId = null

const startedLabel = computed(() => botStatus.value.started_at || '—')

const durationLabel = computed(() => {
  const s = botStatus.value.started_at
  if (!botStatus.value.inbound_enabled || !s) return '—'
  const t = new Date(s).getTime()
  if (!Number.isFinite(t)) return String(s)
  const sec = Math.floor((runtimeTick.value - t) / 1000)
  if (sec < 60) return `${sec} 秒`
  const m = Math.floor(sec / 60)
  return m < 60 ? `${m} 分钟` : `${Math.floor(m / 60)} 小时 ${m % 60} 分`
})

function setSubPage(id) {
  subPage.value = id
  router.replace({ query: { ...route.query, tab: id } })
}

async function refreshTrayWxid() {
  try {
    const t = await getTrayHealth()
    const wx = t?.hook_profile?.wxid || t?.hook_stored_wxid || ''
    if (wx) {
      hookWxid.value = wx
      if (!renewWxid.value) renewWxid.value = wx
    }
  } catch {
    /* ignore */
  }
}

function mergeLicenseFromBot(status = {}, lic = {}) {
  return {
    robot_valid: !!(lic.robot_valid ?? status.robot_valid),
    expire_display: lic.expire_display || status.expire_display || '—',
    demo_auto_license: !!(lic.demo_auto_license ?? status.demo_auto_license),
    integrity_ok: lic.integrity_ok ?? status.integrity_ok ?? true,
    robot_configured: lic.robot_configured ?? status.robot_configured,
    max_groups: lic.max_groups ?? status.max_groups,
    remaining_groups: lic.remaining_groups ?? status.remaining_groups,
    bound_groups: lic.bound_groups ?? status.bound_groups,
    days: lic.days ?? status.days
  }
}

async function loadLicense(status = {}) {
  try {
    const lic = (await getLicenseStatus()) || {}
    licenseStatus.value = mergeLicenseFromBot(status, lic)
  } catch {
    licenseStatus.value = mergeLicenseFromBot(status, {})
  }
}

async function loadBotPanel() {
  const status = (await getBotStatus().catch(() => ({}))) || {}
  botStatus.value = status
  await loadLicense(status)
}

async function loadWorkLogs() {
  const d = await getBotWorkLogs(80)
  workLogs.value = d?.logs || []
}

/** @param hot  true=热注入（不关微信）；默认冷注入 */
async function handleInject(hot = false) {
  injectBusy.value = true
  injectLog.value = hot ? '热注入：保持微信运行…' : '冷注入：正在关闭微信并重新注入…'
  try {
    const d = await runWechatInjectWithPathPrompt(runBotWechatInject, hot)
    if (d?.cancelled) {
      injectLog.value = '已取消：未指定微信路径'
      return
    }
    if (d?.ok) {
      injectLog.value = [d.log, d.warn].filter(Boolean).join('\n') || '注入完成'
      ElMessage.success(d.warn ? 'Hook 已就绪（注入过程有告警）' : '微信 Hook 注入完成')
      await loadBotPanel()
      await refreshTrayWxid()
    } else {
      injectLog.value = [d?.error, d?.stdout].filter(Boolean).join('\n\n') || '注入失败'
      ElMessage.error(d?.error || '注入失败')
    }
  } catch (e) {
    injectLog.value = extractApiError(e, '注入失败')
    ElMessage.error(injectLog.value)
  } finally {
    injectBusy.value = false
  }
}

async function toggleInbound() {
  const next = !botStatus.value.inbound_enabled
  try {
    const d = await setBotInbound(next)
    botStatus.value.inbound_enabled = d.inbound_enabled
    botStatus.value.started_at = d.started_at
    ElMessage.success(next ? '入站已开启' : '入站已暂停')
    await loadWorkLogs()
  } catch (e) {
    ElMessage.error(e?.message || '操作失败')
  }
}

async function runParseTest() {
  parseBusy.value = true
  parseResult.value = ''
  try {
    const d = await parseTest(parseText.value)
    parseResult.value = JSON.stringify(d.result || d, null, 2)
  } catch (e) {
    parseResult.value = e?.message || '试算失败'
  } finally {
    parseBusy.value = false
  }
}

async function submitRenew() {
  renewBusy.value = true
  renewMsg.value = ''
  try {
    const d = await redeemRobotCard({
      wxid: renewWxid.value,
      code: renewCipher.value
    })
    if (d?.success !== false && (d?.ok || d?.expire_date)) {
      renewOk.value = true
      renewMsg.value = `激活成功，到期 ${d.expire_display || d.expire_date}`
      ElMessage.success(renewMsg.value)
      renewCipher.value = ''
      await loadLicense()
      await loadBotPanel()
    } else {
      renewOk.value = false
      renewMsg.value = d?.error || '激活失败'
      ElMessage.error(renewMsg.value)
    }
  } catch (e) {
    renewOk.value = false
    renewMsg.value = e?.message || '激活失败'
    ElMessage.error(renewMsg.value)
  } finally {
    renewBusy.value = false
  }
}

watch(
  () => route.query.tab,
  (tab) => {
    if (tab && tabs.some((t) => t.id === tab)) subPage.value = tab
  },
  { immediate: true }
)

onMounted(async () => {
  await refreshTrayWxid()
  await loadBotPanel()
  await loadWorkLogs()
  pollId = setInterval(async () => {
    runtimeTick.value = Date.now()
    if (subPage.value === 'status') await loadBotPanel()
  }, 15000)
  clockId = setInterval(() => {
    runtimeTick.value = Date.now()
  }, 1000)
})

onUnmounted(() => {
  if (pollId) clearInterval(pollId)
  if (clockId) clearInterval(clockId)
})
</script>

<style scoped lang="scss">
.bot-tab-strip {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.bot-tab {
  text-align: left;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: #fff;
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.06);
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;

  &--active {
    border-color: #5b4ae8;
    box-shadow: 0 4px 24px rgba(91, 74, 232, 0.15);
  }
}

.bot-tab-icon {
  display: inline-block;
  margin-right: 8px;
  color: var(--accent, #5b4ae8);
}

.bot-tab-title {
  font-weight: 600;
  color: #1e293b;
  display: block;
}

.bot-tab-desc {
  font-size: 12px;
  color: #94a3b8;
  display: block;
  margin-top: 4px;
}

.panel-card {
  border-radius: 14px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.muted {
  color: #64748b;
  font-size: 13px;
}

.inject-log,
.parse-result {
  margin-top: 12px;
  padding: 12px;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 12px;
  max-height: 200px;
  overflow: auto;
}

.inbound-row {
  display: flex;
  align-items: center;
  gap: 20px;
}

.inbound-meta {
  font-size: 13px;
  color: #475569;
  line-height: 1.8;
}

.ok-text {
  color: #059669;
}
.err-text {
  color: #dc2626;
}
</style>

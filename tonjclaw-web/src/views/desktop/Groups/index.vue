<template>
  <div class="groups-page desktop-card">
    <section class="group-tab-strip">
      <button
        v-for="t in tabs"
        :key="t.id"
        type="button"
        class="group-tab"
        :class="{ 'group-tab--active': subPage === t.id }"
        @click="setSubPage(t.id)"
      >
        <span class="group-tab-icon" :style="{ color: t.color }">{{ t.icon }}</span>
        <span class="group-tab-title">{{ t.title }}</span>
        <span class="group-tab-desc">{{ t.desc }}</span>
      </button>
    </section>

    <!-- 群列表 -->
    <template v-if="subPage === 'list'">
      <el-alert
        v-if="isDemoBoss"
        type="info"
        show-icon
        :closable="false"
        title="免费测试：1 天 · 最多 3 个群"
        description="演示账号绑定群无需卡密；超过 3 个群需解绑后再绑，或开通正式授权。"
        style="margin-bottom: 12px"
      />
      <div class="toolbar">
        <el-input v-model="searchQuery" placeholder="搜索群名称或 ID" clearable style="max-width: 320px" />
        <el-button :loading="loading" @click="loadGroups(true)">
          <el-icon><Refresh /></el-icon>
          同步 Hook 并刷新
        </el-button>
      </div>
      <el-table v-loading="loading" :data="filteredGroups" border stripe>
        <el-table-column prop="name" label="群名称" min-width="160" />
        <el-table-column prop="wx_group_id" label="群 ID" min-width="200" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_bound ? 'success' : 'info'">
              {{ row.is_bound ? '已绑定' : '未绑定' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="expire_display" label="到期时间" width="160" />
        <el-table-column label="剩余" width="90">
          <template #default="{ row }">
            <span v-if="row.days_left != null">{{ row.days_left }} 天</span>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column prop="member_count" label="人数" width="80" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="!row.is_bound"
              link
              type="primary"
              size="small"
              @click="openBind(row)"
            >
              绑定
            </el-button>
            <el-button
              v-if="row.is_bound"
              link
              type="primary"
              size="small"
              @click="openRenew(row)"
            >
              续期
            </el-button>
            <el-button
              v-if="row.is_bound"
              link
              type="danger"
              size="small"
              @click="handleUnbind(row)"
            >
              解绑
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </template>

    <!-- Hook 群聊 -->
    <template v-if="subPage === 'hook'">
      <el-card shadow="never">
        <p class="muted">从 Hook 控制面拉取群列表并写入本地缓存，供绑定与续期使用。</p>
        <el-button type="primary" :loading="hookLoading" @click="loadHookRooms">
          拉取 Hook 群列表
        </el-button>
        <el-table v-if="hookRooms.length" :data="hookRooms" border style="margin-top: 16px" max-height="400">
          <el-table-column prop="nickName" label="群昵称" min-width="160" />
          <el-table-column prop="wxid" label="群 ID" min-width="200" show-overflow-tooltip />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="importFromHook(row)">
                导入绑定
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <!-- 群续期（原 license_v2 桌面能力） -->
    <template v-if="subPage === 'renew'">
      <el-alert type="info" show-icon :closable="false" style="margin-bottom: 16px">
        群级授权通过 SimBot 管理平台下发的卡密核销，成功后同步写入本地群配置与 license_v2（bound_to=群ID）。
      </el-alert>

      <el-card shadow="never" style="margin-bottom: 16px">
        <template #header>单群续期</template>
        <el-form label-width="100px">
          <el-form-item label="群 ID">
            <el-input v-model="renewForm.wx_group_id" placeholder="xxx@chatroom" />
          </el-form-item>
          <el-form-item label="卡密">
            <el-input v-model="renewForm.code" type="textarea" :rows="4" placeholder="SimBot 群续期卡密" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="renewBusy" @click="submitRenew">核销续期</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card shadow="never">
        <template #header>批量续期</template>
        <p class="muted">勾选下方已绑定群，每行一个卡密，行序与勾选顺序一致。</p>
        <el-table
          ref="batchTableRef"
          :data="boundGroups"
          border
          @selection-change="onBatchSelect"
        >
          <el-table-column type="selection" width="48" />
          <el-table-column prop="name" label="群名称" />
          <el-table-column prop="wx_group_id" label="群 ID" show-overflow-tooltip />
          <el-table-column prop="expire_display" label="当前到期" width="160" />
        </el-table>
        <el-input
          v-model="batchCodesText"
          type="textarea"
          :rows="6"
          placeholder="每行一个卡密"
          style="margin-top: 12px"
        />
        <el-button type="primary" :loading="batchBusy" style="margin-top: 12px" @click="submitBatchRenew">
          批量核销
        </el-button>
      </el-card>
    </template>

    <el-dialog v-model="bindVisible" :title="bindTarget?.is_bound ? '群续期' : '绑定并开通'" width="520px">
      <p v-if="bindTarget" class="muted">{{ bindTarget.name }} — {{ bindTarget.wx_group_id }}</p>
      <el-input v-model="bindCode" type="textarea" :rows="5" placeholder="粘贴 SimBot 群续期卡密（绑定未开通群必填）" />
      <template #footer>
        <el-button @click="bindVisible = false">取消</el-button>
        <el-button type="primary" :loading="bindBusy" @click="submitBindDialog">
          {{ bindTarget?.is_bound ? '续期' : '绑定并开通' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import {
  getGroups,
  getHookChatrooms,
  bindGroup,
  redeemGroup,
  unbindGroup,
  batchRedeemGroups
} from '../../../api/desktop/groups'
import { useUserStore } from '../../../stores/user'
import { isDemoBossUser } from '../../../utils/demoBossTrial'

const route = useRoute()
const userStore = useUserStore()
const isDemoBoss = computed(() => isDemoBossUser(userStore.userInfo))
const router = useRouter()

const tabs = [
  { id: 'list', title: '群列表', desc: 'Hook 缓存 + 绑定状态', icon: '☰', color: '#5b4ae8' },
  { id: 'hook', title: 'Hook 群聊', desc: '拉取并导入', icon: '💬', color: '#0d9488' },
  { id: 'renew', title: '群续期', desc: 'SimBot 卡密核销', icon: '🔑', color: '#f97316' }
]

const subPage = ref('list')
const groups = ref([])
const loading = ref(false)
const searchQuery = ref('')
const hookRooms = ref([])
const hookLoading = ref(false)
const bindVisible = ref(false)
const bindTarget = ref(null)
const bindCode = ref('')
const bindBusy = ref(false)
const renewForm = ref({ wx_group_id: '', code: '' })
const renewBusy = ref(false)
const batchSelection = ref([])
const batchCodesText = ref('')
const batchBusy = ref(false)

let pollId = null
let lastRevision = ''

const filteredGroups = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return groups.value
  return groups.value.filter((g) => {
    const id = String(g.wx_group_id || '').toLowerCase()
    const name = String(g.name || '').toLowerCase()
    return id.includes(q) || name.includes(q)
  })
})

const boundGroups = computed(() => groups.value.filter((g) => g.is_bound))

function setSubPage(id) {
  subPage.value = id
  router.replace({ query: { ...route.query, tab: id } })
}

async function loadGroups(sync = true) {
  loading.value = true
  try {
    const data = await getGroups({ sync })
    groups.value = data.groups || []
    lastRevision = data.groups_desk_revision || ''
  } catch (e) {
    ElMessage.error(e?.message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function loadHookRooms() {
  hookLoading.value = true
  try {
    const data = await getHookChatrooms()
    const items = data.items || data.chatrooms || []
    hookRooms.value = items.map((it) => ({
      wxid: it.username || it.wxid || it.room_id || it.userName,
      nickName: it.nick_name || it.nickName || it.nickname || it.name || it.remark || it.wxid
    }))
    const cached = data.cached ?? data.synced
    ElMessage.success(
      cached != null
        ? `已缓存 ${cached} 个群（Hook 共 ${hookRooms.value.length} 个）`
        : `已缓存 ${hookRooms.value.length} 个群`
    )
    await loadGroups(true)
  } catch (e) {
    ElMessage.error(e?.message || '拉取失败')
  } finally {
    hookLoading.value = false
  }
}

function openBind(row) {
  bindTarget.value = row
  bindCode.value = ''
  bindVisible.value = true
}

function openRenew(row) {
  renewForm.value.wx_group_id = row.wx_group_id
  renewForm.value.code = ''
  setSubPage('renew')
}

async function submitBindDialog() {
  if (!bindTarget.value) return
  const code = bindCode.value.trim()
  if (!bindTarget.value.is_bound && !code) {
    ElMessage.warning('未绑定群须填写卡密')
    return
  }
  bindBusy.value = true
  try {
    if (code) {
      await redeemGroup({ wx_group_id: bindTarget.value.wx_group_id, code })
      ElMessage.success('群已绑定并开通')
    } else {
      await bindGroup({
        wx_group_id: bindTarget.value.wx_group_id,
        name: bindTarget.value.name
      })
      ElMessage.success('群已绑定')
    }
    bindVisible.value = false
    await loadGroups(false)
  } catch (e) {
    ElMessage.error(e?.message || '操作失败')
  } finally {
    bindBusy.value = false
  }
}

async function handleUnbind(row) {
  await ElMessageBox.confirm(`确定解绑群「${row.name}」？解绑后不再处理该群消息。`, '提示', { type: 'warning' })
  try {
    await unbindGroup(row.wx_group_id)
    ElMessage.success('已解绑')
    await loadGroups(false)
  } catch (e) {
    ElMessage.error(e?.message || '解绑失败')
  }
}

async function importFromHook(row) {
  try {
    await bindGroup({ wx_group_id: row.wxid, name: row.nickName })
    ElMessage.success('已导入绑定，请至群续期粘贴卡密开通')
    await loadGroups(false)
  } catch (e) {
    ElMessage.error(e?.message || '导入失败')
  }
}

async function submitRenew() {
  renewBusy.value = true
  try {
    await redeemGroup({
      wx_group_id: renewForm.value.wx_group_id,
      code: renewForm.value.code
    })
    ElMessage.success('群续期成功')
    renewForm.value.code = ''
    await loadGroups(false)
  } catch (e) {
    ElMessage.error(e?.message || '续期失败')
  } finally {
    renewBusy.value = false
  }
}

function onBatchSelect(rows) {
  batchSelection.value = rows
}

async function submitBatchRenew() {
  const ids = batchSelection.value.map((r) => r.wx_group_id)
  const codes = batchCodesText.value.split('\n').map((s) => s.trim()).filter(Boolean)
  if (!ids.length) {
    ElMessage.warning('请勾选至少一个群')
    return
  }
  if (ids.length !== codes.length) {
    ElMessage.warning('卡密行数须与勾选群数一致')
    return
  }
  batchBusy.value = true
  try {
    const d = await batchRedeemGroups(ids, codes)
    if (d.success) {
      ElMessage.success('批量续期完成')
      batchCodesText.value = ''
      await loadGroups(false)
    }
  } catch (e) {
    ElMessage.error(e?.message || '批量续期失败')
  } finally {
    batchBusy.value = false
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
  await loadGroups(true)
  pollId = setInterval(async () => {
    try {
      const data = await getGroups({ sync: false })
      const rev = data.groups_desk_revision || ''
      if (rev && lastRevision && rev !== lastRevision) {
        await loadGroups(false)
      }
      if (!lastRevision && rev) lastRevision = rev
    } catch {
      /* ignore */
    }
  }, 5000)
})

onUnmounted(() => {
  if (pollId) clearInterval(pollId)
})
</script>

<style scoped lang="scss">
.group-tab-strip {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}
.group-tab {
  text-align: left;
  padding: 14px 16px;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: #fff;
  cursor: pointer;
  &--active {
    border-color: #5b4ae8;
    box-shadow: 0 4px 24px rgba(91, 74, 232, 0.12);
  }
}
.group-tab-title {
  font-weight: 600;
  display: block;
}
.group-tab-desc {
  font-size: 12px;
  color: #94a3b8;
  display: block;
  margin-top: 4px;
}
.toolbar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  align-items: center;
}
.muted {
  color: #64748b;
  font-size: 13px;
}
</style>

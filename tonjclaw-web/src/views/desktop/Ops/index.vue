<template>
  <div class="desktop-ops desktop-card">
    <h2 class="page-title">系统运维</h2>
    <p class="page-desc muted">本地数据备份与 SimBot 管理平台连接状态（仅桌面端）</p>

    <el-row :gutter="20">
      <el-col :span="12">
        <el-card shadow="never" class="ops-card">
          <template #header>数据备份</template>
          <p class="muted">数据库：{{ backupStatus.sqlite_path || '—' }}</p>
          <p class="muted">备份目录：{{ backupStatus.backup_dir || '—' }}</p>
          <el-button type="primary" :loading="backupBusy" @click="handleBackup">
            立即备份 SQLite
          </el-button>
          <el-table v-if="backupStatus.files?.length" :data="backupStatus.files" size="small" style="margin-top: 16px">
            <el-table-column prop="name" label="文件名" />
            <el-table-column prop="mtime" label="时间" width="180" />
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="ops-card">
          <template #header>SimBot 管理平台</template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="平台地址">
              {{ backupStatus.platform_url || '未配置 SIMBOT_PLATFORM_URL' }}
            </el-descriptions-item>
            <el-descriptions-item label="说明">
              主程序卡密由 SimBot 管理平台签发；桌面端使用同一公钥/平台 API 核销后写入本地授权。
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getOpsBackupStatus, runOpsBackup } from '../../../api/desktop/bot'

const backupStatus = ref({})
const backupBusy = ref(false)

async function load() {
  try {
    backupStatus.value = (await getOpsBackupStatus()) || {}
  } catch (e) {
    ElMessage.error(e?.message || '加载失败')
  }
}

async function handleBackup() {
  backupBusy.value = true
  try {
    const d = await runOpsBackup()
    if (d?.ok) {
      ElMessage.success(`备份完成：${d.path}`)
      await load()
    }
  } catch (e) {
    ElMessage.error(e?.message || '备份失败')
  } finally {
    backupBusy.value = false
  }
}

onMounted(load)
</script>

<style scoped lang="scss">
.page-title {
  margin: 0 0 8px;
  font-size: 20px;
  color: #1e293b;
}
.page-desc {
  margin: 0 0 20px;
  font-size: 13px;
}
.muted {
  color: #64748b;
}
.ops-card {
  border-radius: 14px;
}
</style>

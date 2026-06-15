<template>
  <div class="user-rules">
    <h2 class="section-title">规则备份</h2>
    
    <el-alert
      title="您可以将自己的规则配置备份到云端，方便在多台设备间同步。请到桌面端应用中使用云端规则模板。"
      type="info"
      :closable="false"
      style="margin-bottom: 20px;"
    ></el-alert>

    <el-button type="primary" @click="uploadBackup" style="margin-bottom: 15px;">
      <el-icon><Upload /></el-icon> 上传新备份
    </el-button>
    
    <el-table :data="myBackups" style="width: 100%" v-loading="backupsLoading">
      <el-table-column prop="backup_name" label="备份名称" width="200"></el-table-column>
      <el-table-column prop="version" label="版本" width="100"></el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column prop="is_current" label="当前使用" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.is_current" type="success" size="small">是</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button size="small" @click="downloadMyBackup(row)">下载</el-button>
          <el-button size="small" type="primary" @click="applyBackup(row)">应用</el-button>
          <el-button size="small" type="danger" @click="deleteMyBackup(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="myBackups.length === 0 && !backupsLoading" description="暂无备份记录"></el-empty>


  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'
import request from '../../../utils/request'

const myBackups = ref([])
const backupsLoading = ref(false)

const loadMyBackups = async () => {
  backupsLoading.value = true
  try {
    const res = await request.get('/api/rule-templates/backups')
    if (res.success) myBackups.value = res.backups || []
  } catch (error) {
    ElMessage.error('加载备份列表失败')
  } finally {
    backupsLoading.value = false
  }
}

const uploadBackup = async () => {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.json'
  input.onchange = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    try {
      const text = await file.text()
      const backupData = JSON.parse(text)
      const res = await request.post('/api/rule-templates/backups', {
        backup_name: file.name.replace('.json', ''),
        parse_rules: backupData.parse_rules || [],
        stat_rules: backupData.stat_rules || [],
        reply_rules: backupData.reply_rules || [],
        version: backupData.version || '1.0'
      })
      if (res.success) {
        ElMessage.success('备份上传成功')
        loadMyBackups()
      } else {
        ElMessage.error(res.error || '上传失败')
      }
    } catch (err) {
      ElMessage.error('文件格式错误或上传失败')
    }
  }
  input.click()
}

const downloadMyBackup = (backup) => {
  const backupData = {
    parse_rules: backup.parse_rules || [],
    stat_rules: backup.stat_rules || [],
    reply_rules: backup.reply_rules || [],
    version: backup.version || '1.0'
  }
  const dataStr = JSON.stringify(backupData, null, 2)
  const blob = new Blob([dataStr], {type: 'application/json'})
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${backup.backup_name}.json`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  ElMessage.success('备份下载成功')
}

const applyBackup = (backup) => {
  ElMessage.info('请将此备份文件导入到桌面端应用中')
}

const deleteMyBackup = async (backup) => {
  try {
    await ElMessageBox.confirm(`确定要删除备份 "${backup.backup_name}" 吗？`, '警告', { type: 'warning' })
    const res = await request.delete(`/api/rule-templates/backups/${backup.id}`)
    if (res.success) {
      ElMessage.success('备份删除成功')
      loadMyBackups()
    } else {
      ElMessage.error(res.error || '删除失败')
    }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('网络请求失败')
  }
}

const formatDate = (dateStr) => dateStr ? new Date(dateStr).toLocaleString('zh-CN') : '-'

onMounted(() => {
  loadMyBackups()
})
</script>

<style scoped lang="scss">
.user-rules {
  .section-title {
    font-size: 20px;
    margin-bottom: 20px;
    color: #1e293b;
  }
  
  .filter-bar {
    margin-bottom: 20px;
    display: flex;
    gap: 10px;
    align-items: center;
  }
}
</style>

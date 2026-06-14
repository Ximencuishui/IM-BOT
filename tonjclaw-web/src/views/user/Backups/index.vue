<template>
  <div class="user-backups">
    <div class="header-actions">
      <h2 class="section-title">备份文件管理</h2>
      <el-upload
        action="#"
        :auto-upload="false"
        :on-change="handleFileSelect"
        accept=".json,.csv,.txt,.md"
        :show-file-list="false"
      >
        <el-button type="primary">
          <el-icon><Upload /></el-icon> 上传备份
        </el-button>
      </el-upload>
    </div>

    <el-alert
      title="提示: 备份文件仅存储规则配置,不包含业务数据。业务数据请在本地桌面端备份。"
      type="info"
      :closable="false"
      style="margin-bottom: 20px;"
    ></el-alert>

    <div v-loading="loading">
      <el-card v-for="backup in backups" :key="backup.id" class="backup-item">
        <div class="backup-info">
          <el-icon class="file-icon"><Document /></el-icon>
          <div>
            <div class="filename"><strong>{{ backup.filename }}</strong></div>
            <div class="meta">
              {{ formatFileSize(backup.size) }} · {{ formatDate(backup.uploaded_at) }}
            </div>
          </div>
        </div>
        <div class="backup-actions">
          <el-button size="small" @click="downloadBackup(backup)">下载</el-button>
          <el-button size="small" type="danger" @click="deleteBackup(backup)">删除</el-button>
        </div>
      </el-card>

      <el-empty v-if="backups.length === 0 && !loading" description="暂无备份文件"></el-empty>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, Document } from '@element-plus/icons-vue'
import request from '../../../utils/request'

const loading = ref(false)
const backups = ref([])

const loadBackups = async () => {
  loading.value = true
  try {
    const res = await request.get('/api/backups')
    if (res.success) {
      backups.value = res.backups || []
    } else {
      ElMessage.error(res.error || '加载失败')
    }
  } catch (error) {
    console.error('加载备份列表失败:', error)
  } finally {
    loading.value = false
  }
}

const handleFileSelect = async (file) => {
  // 限制文件大小为 10MB
  const isLt10M = file.size / 1024 / 1024 < 10
  if (!isLt10M) {
    ElMessage.error('上传文件大小不能超过 10MB!')
    return
  }

  const formData = new FormData()
  formData.append('file', file.raw)
  
  try {
    const res = await request.post('/api/backups/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    if (res.success) {
      ElMessage.success('上传成功')
      loadBackups()
    } else {
      ElMessage.error(res.error || '上传失败')
    }
  } catch (error) {
    ElMessage.error('网络请求失败')
  }
}

const downloadBackup = (backup) => {
  window.open(`${import.meta.env.VITE_API_BASE_URL}/api/backups/${backup.id}/download`, '_blank')
}

const deleteBackup = async (backup) => {
  try {
    await ElMessageBox.confirm('确定删除此备份文件?', '提示', { type: 'warning' })
    const res = await request.delete(`/api/backups/${backup.id}`)
    if (res.success) {
      ElMessage.success('删除成功')
      loadBackups()
    } else {
      ElMessage.error(res.error || '删除失败')
    }
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('操作失败')
  }
}

const formatDate = (dateStr) => dateStr ? new Date(dateStr).toLocaleString('zh-CN') : '-'

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

onMounted(() => {
  loadBackups()
})
</script>

<style scoped lang="scss">
.user-backups {
  .header-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    
    .section-title {
      margin: 0;
      font-size: 20px;
      color: #1e293b;
    }
  }

  .backup-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 15px;
    margin-bottom: 10px;
    
    .backup-info {
      display: flex;
      align-items: center;
      gap: 10px;
      
      .file-icon {
        font-size: 24px;
        color: #409EFF;
      }
      
      .filename {
        font-size: 14px;
        color: #303133;
      }
      
      .meta {
        font-size: 12px;
        color: #909399;
        margin-top: 2px;
      }
    }
  }
}
</style>

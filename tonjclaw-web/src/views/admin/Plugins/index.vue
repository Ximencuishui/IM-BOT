<template>
  <div class="admin-plugins">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.total_plugins }}</div>
          <div class="stat-label">插件总数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.active_plugins }}</div>
          <div class="stat-label">已上架</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.total_installs }}</div>
          <div class="stat-label">总安装量</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ stats.monthly_installs }}</div>
          <div class="stat-label">本月新增安装</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 搜索和操作栏 -->
    <el-card class="search-card">
      <el-row :gutter="16">
        <el-col :span="6">
          <el-input v-model="searchForm.search" placeholder="搜索插件名称/代码/描述" clearable @clear="fetchPlugins" @keyup.enter="fetchPlugins" />
        </el-col>
        <el-col :span="4">
          <el-select v-model="searchForm.category" placeholder="分类筛选" clearable @change="fetchPlugins" style="width:100%">
            <el-option label="全部" value="" />
            <el-option v-for="cat in categories" :key="cat.value" :label="cat.label" :value="cat.value" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-select v-model="searchForm.status" placeholder="状态筛选" clearable @change="fetchPlugins" style="width:100%">
            <el-option label="全部" value="" />
            <el-option label="已上架" value="active" />
            <el-option label="未上架" value="inactive" />
            <el-option label="已废弃" value="deprecated" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-select v-model="searchForm.industry" placeholder="行业筛选" clearable @change="fetchPlugins" style="width:100%">
            <el-option label="全部" value="" />
            <el-option v-for="ind in industries" :key="ind" :label="ind" :value="ind" />
          </el-select>
        </el-col>
        <el-col :span="6" style="text-align: right;">
          <el-button type="primary" @click="showCreateDialog">
            <el-icon><Plus /></el-icon>新建插件
          </el-button>
          <el-button @click="fetchPlugins">
            <el-icon><Refresh /></el-icon>刷新
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 插件表格 -->
    <el-card>
      <el-table :data="plugins" v-loading="loading" stripe style="width:100%" max-height="600">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column label="图标" width="60">
          <template #default="{ row }">
            <span style="font-size:24px">{{ row.icon_url || '🧩' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="名称" min-width="160">
          <template #default="{ row }">
            <div>
              <strong>{{ row.plugin_name }}</strong>
              <el-tag size="small" style="margin-left:6px">{{ row.plugin_code }}</el-tag>
            </div>
            <div style="font-size:12px;color:#909399;margin-top:2px;">{{ row.short_description || row.description?.slice(0, 60) }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="100">
          <template #default="{ row }">
            <el-tag :type="categoryType(row.category)" size="small">{{ categoryLabel(row.category) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="industry" label="行业" width="100" />
        <el-table-column label="版本" width="80" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.latest_version || '-' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <div style="display:flex;gap:4px;flex-wrap:wrap;">
              <el-tag v-if="row.is_active && row.is_public" type="success" size="small">已上架</el-tag>
              <el-tag v-else-if="row.is_deprecated" type="danger" size="small">已废弃</el-tag>
              <el-tag v-else type="warning" size="small">未上架</el-tag>
              <el-tag v-if="row.is_featured" type="danger" size="small">推荐</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="download_count" label="下载量" width="80" align="center" />
        <el-table-column prop="rating" label="评分" width="70" align="center">
          <template #default="{ row }">{{ row.rating?.toFixed(1) || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="showEditDialog(row)">编辑</el-button>
            <el-button size="small" @click="showVersionsDialog(row)">版本</el-button>
            <el-dropdown trigger="click" @command="(cmd) => handleAction(cmd, row)">
              <el-button size="small">
                更多<el-icon><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="toggleActive">{{ row.is_active ? '下架' : '上架' }}</el-dropdown-item>
                  <el-dropdown-item v-if="!row.is_deprecated" command="toggleFeatured">{{ row.is_featured ? '取消推荐' : '设为推荐' }}</el-dropdown-item>
                  <el-dropdown-item command="toggleDeprecated" divided>标记废弃</el-dropdown-item>
                  <el-dropdown-item command="delete" divided>删除插件</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>
      <div style="margin-top:16px;text-align:right;">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @change="fetchPlugins"
        />
      </div>
    </el-card>

    <!-- 创建/编辑插件对话框 -->
    <el-dialog v-model="dialogVisible" :title="isEditing ? '编辑插件' : '新建插件'" width="720px" :close-on-click-modal="false">
      <el-form :model="form" :rules="formRules" ref="formRef" label-width="100px" label-position="top">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="插件名称" prop="plugin_name">
              <el-input v-model="form.plugin_name" placeholder="例如：餐饮配送插件" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="插件代码" prop="plugin_code">
              <el-input v-model="form.plugin_code" placeholder="例如：fooddelivery" :disabled="isEditing" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="详细描述">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="插件功能详细描述" />
        </el-form-item>
        <el-form-item label="简短描述">
          <el-input v-model="form.short_description" placeholder="列表展示用简短描述" maxlength="100" show-word-limit />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="分类" prop="category">
              <el-select v-model="form.category" placeholder="选择分类" style="width:100%">
                <el-option v-for="cat in categories" :key="cat.value" :label="cat.label" :value="cat.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="所属行业">
              <el-select v-model="form.industry" placeholder="选择行业" clearable style="width:100%">
                <el-option v-for="ind in industries" :key="ind" :label="ind" :value="ind" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="图标">
              <el-input v-model="form.icon_url" placeholder="emoji 或 URL" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="标签">
          <el-input v-model="form.tags" placeholder="逗号分隔，例如：餐饮,配送,订单" />
        </el-form-item>
        <el-divider>状态设置</el-divider>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-switch v-model="form.is_public" active-text="公开" inactive-text="隐藏" />
          </el-col>
          <el-col :span="8">
            <el-switch v-model="form.is_active" active-text="上架" inactive-text="下架" />
          </el-col>
          <el-col :span="8">
            <el-switch v-model="form.is_featured" active-text="推荐" />
          </el-col>
        </el-row>
        <el-row :gutter="20" style="margin-top:16px;">
          <el-col :span="12">
            <el-form-item label="评分">
              <el-slider v-model="form.rating" :min="0" :max="5" :step="0.1" show-input style="width:200px" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="下载量">
              <el-input-number v-model="form.download_count" :min="0" style="width:160px" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">{{ isEditing ? '保存修改' : '创建插件' }}</el-button>
      </template>
    </el-dialog>

    <!-- 版本管理对话框 -->
    <el-dialog v-model="versionsVisible" title="版本管理" width="800px" :close-on-click-modal="false">
      <template v-if="currentPlugin">
        <div style="margin-bottom:16px;">
          <strong>{{ currentPlugin.plugin_name }}</strong>
          <el-tag size="small" style="margin-left:8px">{{ currentPlugin.plugin_code }}</el-tag>
        </div>
        <el-table :data="versions" stripe style="width:100%" v-loading="versionsLoading">
          <el-table-column prop="version" label="版本号" width="100" />
          <el-table-column label="稳定版" width="80" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.is_stable" type="success" size="small">稳定</el-tag>
              <el-tag v-else type="warning" size="small">测试</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="file_size" label="文件大小" width="100" align="right">
            <template #default="{ row }">{{ formatSize(row.file_size) }}</template>
          </el-table-column>
          <el-table-column label="状态" width="70" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.is_active" type="success" size="small">启用</el-tag>
              <el-tag v-else type="danger" size="small">禁用</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="changelog" label="更新日志" min-width="180" show-overflow-tooltip />
          <el-table-column prop="created_at" label="创建时间" width="160" />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button size="small" @click="toggleVersionActive(row)">{{ row.is_active ? '禁用' : '启用' }}</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-divider>创建新版本</el-divider>
        <el-form :model="versionForm" label-width="100px">
          <el-row :gutter="16">
            <el-col :span="8">
              <el-form-item label="版本号">
                <el-input v-model="versionForm.version" placeholder="如 2.0.0" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="文件大小">
                <el-input-number v-model="versionForm.file_size" :min="0" style="width:140px" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="下载URL">
                <el-input v-model="versionForm.download_url" placeholder="插件包下载地址" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="更新日志">
            <el-input v-model="versionForm.changelog" type="textarea" :rows="2" placeholder="版本更新内容" />
          </el-form-item>
          <el-row :gutter="16">
            <el-col :span="8">
              <el-switch v-model="versionForm.is_stable" active-text="稳定版" />
            </el-col>
            <el-col :span="16" style="text-align:right;">
              <el-button type="primary" @click="submitVersion" :loading="versionSubmitting">创建版本</el-button>
            </el-col>
          </el-row>
        </el-form>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, ArrowDown } from '@element-plus/icons-vue'
import axios from 'axios'

const API_BASE = ''

// 分类映射
const categories = [
  { value: 'industry', label: '行业插件' },
  { value: 'knowledge', label: '知识库' },
  { value: 'qa', label: '问答库' },
  { value: 'algorithm', label: '解析算法' },
  { value: 'tool', label: '工具插件' },
  { value: 'core', label: '核心插件' },
  { value: 'desktop', label: '桌面端插件' }
]

const categoryLabel = (v) => categories.find(c => c.value === v)?.label || v
const categoryType = (v) => {
  const map = { industry: 'success', knowledge: 'primary', qa: 'warning', algorithm: 'info', tool: '', core: 'danger', desktop: '' }
  return map[v] || 'info'
}

const industries = ref([])
const plugins = ref([])
const loading = ref(false)
const submitting = ref(false)

// 统计
const stats = reactive({
  total_plugins: 0,
  active_plugins: 0,
  total_installs: 0,
  monthly_installs: 0
})

// 搜索
const searchForm = reactive({
  search: '',
  category: '',
  status: '',
  industry: ''
})

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 创建/编辑对话框
const dialogVisible = ref(false)
const isEditing = ref(false)
const editingId = ref(null)
const formRef = ref(null)
const form = reactive({
  plugin_name: '',
  plugin_code: '',
  description: '',
  short_description: '',
  category: 'industry',
  industry: '',
  icon_url: '',
  tags: '',
  is_public: true,
  is_active: true,
  is_featured: false,
  rating: 3.0,
  download_count: 0
})

const formRules = {
  plugin_name: [{ required: true, message: '请输入插件名称', trigger: 'blur' }],
  plugin_code: [{ required: true, message: '请输入插件代码', trigger: 'blur' }],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }]
}

// 版本管理对话框
const versionsVisible = ref(false)
const versionsLoading = ref(false)
const versions = ref([])
const currentPlugin = ref(null)
const versionSubmitting = ref(false)
const versionForm = reactive({
  version: '',
  changelog: '',
  download_url: '',
  file_size: 0,
  is_stable: false
})

// 获取统计数据
const fetchStats = async () => {
  try {
    const res = await axios.get(`${API_BASE}/api/plugin/admin/stats`)
    if (res.data.success) {
      Object.assign(stats, res.data.stats)
    }
  } catch {
    // ignore
  }
}

// 获取插件列表
const fetchPlugins = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
      ...searchForm
    }
    Object.keys(params).forEach(k => { if (!params[k]) delete params[k] })

    const res = await axios.get(`${API_BASE}/api/plugin/admin/plugins`, { params })
    if (res.data.success) {
      plugins.value = res.data.plugins || []
      pagination.total = res.data.count || 0
    }
  } catch (e) {
    ElMessage.error('获取插件列表失败: ' + (e.response?.data?.error || e.message))
  } finally {
    loading.value = false
  }
}

// 获取行业列表
const fetchIndustries = async () => {
  try {
    const res = await axios.get(`${API_BASE}/api/plugin/market`)
    if (res.data.success) {
      const inds = [...new Set((res.data.plugins || []).map(p => p.industry).filter(Boolean))]
      industries.value = inds
    }
  } catch {
    industries.value = ['餐饮配送', '生鲜', '零售', '火锅', '零食']
  }
}

// 显示创建对话框
const showCreateDialog = () => {
  isEditing.value = false
  editingId.value = null
  Object.assign(form, {
    plugin_name: '',
    plugin_code: '',
    description: '',
    short_description: '',
    category: 'industry',
    industry: '',
    icon_url: '',
    tags: '',
    is_public: true,
    is_active: true,
    is_featured: false,
    rating: 3.0,
    download_count: 0
  })
  dialogVisible.value = true
}

// 显示编辑对话框
const showEditDialog = (row) => {
  isEditing.value = true
  editingId.value = row.id
  Object.assign(form, {
    plugin_name: row.plugin_name,
    plugin_code: row.plugin_code,
    description: row.description || '',
    short_description: row.short_description || '',
    category: row.category,
    industry: row.industry || '',
    icon_url: row.icon_url || '',
    tags: row.tags || '',
    is_public: !!row.is_public,
    is_active: !!row.is_active,
    is_featured: !!row.is_featured,
    rating: row.rating || 0,
    download_count: row.download_count || 0
  })
  dialogVisible.value = true
}

// 提交表单
const submitForm = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const payload = { ...form }
    if (isEditing.value) {
      const res = await axios.put(`${API_BASE}/api/plugin/admin/plugins/${editingId.value}`, payload)
      if (res.data.success) {
        ElMessage.success('插件已更新')
        dialogVisible.value = false
        await fetchPlugins()
        await fetchStats()
      } else {
        ElMessage.error(res.data.error || '更新失败')
      }
    } else {
      const res = await axios.post(`${API_BASE}/api/plugin/admin/plugins`, payload)
      if (res.data.success) {
        ElMessage.success('插件已创建')
        dialogVisible.value = false
        await fetchPlugins()
        await fetchStats()
      } else {
        ElMessage.error(res.data.error || '创建失败')
      }
    }
  } catch (e) {
    ElMessage.error('操作失败: ' + (e.response?.data?.error || e.message))
  } finally {
    submitting.value = false
  }
}

// 操作处理
const handleAction = async (cmd, row) => {
  switch (cmd) {
    case 'toggleActive':
      await toggleActive(row)
      break
    case 'toggleFeatured':
      await toggleFeatured(row)
      break
    case 'toggleDeprecated':
      await markDeprecated(row)
      break
    case 'delete':
      await deletePlugin(row)
      break
  }
}

const toggleActive = async (row) => {
  try {
    const res = await axios.put(`${API_BASE}/api/plugin/admin/plugins/${row.id}/status`, {
      is_active: !row.is_active
    })
    if (res.data.success) {
      ElMessage.success(row.is_active ? '插件已下架' : '插件已上架')
      await fetchPlugins()
    }
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const toggleFeatured = async (row) => {
  try {
    const res = await axios.put(`${API_BASE}/api/plugin/admin/plugins/${row.id}/status`, {
      is_featured: !row.is_featured
    })
    if (res.data.success) {
      ElMessage.success(row.is_featured ? '已取消推荐' : '已设为推荐')
      await fetchPlugins()
    }
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const markDeprecated = async (row) => {
  try {
    await ElMessageBox.confirm(`确定将插件「${row.plugin_name}」标记为废弃？`, '确认', {
      confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning'
    })
    const res = await axios.put(`${API_BASE}/api/plugin/admin/plugins/${row.id}/status`, {
      is_deprecated: true, is_active: false
    })
    if (res.data.success) {
      ElMessage.success('插件已标记废弃')
      await fetchPlugins()
    }
  } catch {
    // cancelled
  }
}

const deletePlugin = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除插件「${row.plugin_name}」？此操作不可恢复。`, '确认', {
      confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning'
    })
    const res = await axios.delete(`${API_BASE}/api/plugin/admin/plugins/${row.id}`)
    if (res.data.success) {
      ElMessage.success('插件已删除')
      await fetchPlugins()
      await fetchStats()
    }
  } catch {
    // cancelled
  }
}

// 版本管理
const showVersionsDialog = async (row) => {
  currentPlugin.value = row
  versionsVisible.value = true
  versionsLoading.value = true
  versionForm.version = ''
  versionForm.changelog = ''
  versionForm.download_url = ''
  versionForm.file_size = 0
  versionForm.is_stable = false
  try {
    const res = await axios.get(`${API_BASE}/api/plugin/admin/plugins/${row.id}/versions`)
    if (res.data.success) {
      versions.value = res.data.versions || []
    } else {
      versions.value = []
    }
  } catch {
    versions.value = []
    ElMessage.error('获取版本列表失败')
  } finally {
    versionsLoading.value = false
  }
}

const toggleVersionActive = async (ver) => {
  try {
    // Versions toggle uses same pattern as plugin status, but no dedicated endpoint
    // For simplicity use the same endpoint with version info
    ElMessage.info('版本启用/禁用功能需要后端支持')
  } catch {
    // ignore
  }
}

const submitVersion = async () => {
  if (!versionForm.version) {
    ElMessage.warning('请输入版本号')
    return
  }
  if (!currentPlugin.value) return
  versionSubmitting.value = true
  try {
    const res = await axios.post(`${API_BASE}/api/plugin/admin/plugins/${currentPlugin.value.id}/versions`, {
      ...versionForm
    })
    if (res.data.success) {
      ElMessage.success('版本已创建')
      versionForm.version = ''
      versionForm.changelog = ''
      versionForm.download_url = ''
      versionForm.file_size = 0
      versionForm.is_stable = false
      // Refresh versions
      const vr = await axios.get(`${API_BASE}/api/plugin/admin/plugins/${currentPlugin.value.id}/versions`)
      if (vr.data.success) versions.value = vr.data.versions || []
    } else {
      ElMessage.error(res.data.error || '创建版本失败')
    }
  } catch (e) {
    ElMessage.error('创建版本失败: ' + (e.response?.data?.error || e.message))
  } finally {
    versionSubmitting.value = false
  }
}

const formatSize = (bytes) => {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + 'B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'KB'
  return (bytes / (1024 * 1024)).toFixed(1) + 'MB'
}

onMounted(() => {
  fetchStats()
  fetchPlugins()
  fetchIndustries()
})
</script>

<style scoped lang="scss">
.admin-plugins {
  .stats-row {
    margin-bottom: 20px;
    .stat-card {
      text-align: center;
      .stat-value {
        font-size: 28px;
        font-weight: bold;
        color: #303133;
      }
      .stat-label {
        font-size: 14px;
        color: #909399;
        margin-top: 4px;
      }
    }
  }
  .search-card {
    margin-bottom: 20px;
  }
}
</style>
<template>
  <div class="rules-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>规则库管理</h2>
      <div class="header-actions">
        <el-button type="primary" @click="showImportDialog = true">
          <el-icon><Upload /></el-icon> 导入规则
        </el-button>
        <el-button @click="handleExportRules">
          <el-icon><Download /></el-icon> 导出规则
        </el-button>
        <el-button type="success" @click="showTemplateDialog('create')">
          <el-icon><Plus /></el-icon> 新建模板
        </el-button>
      </div>
    </div>

    <!-- 规则模板列表 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>规则模板</span>
          <el-input
            v-model="searchKeyword"
            placeholder="搜索模板名称"
            style="width: 300px"
            clearable
            @clear="loadTemplates"
            @keyup.enter="loadTemplates"
          >
            <template #append>
              <el-button @click="loadTemplates">
                <el-icon><Search /></el-icon>
              </el-button>
            </template>
          </el-input>
        </div>
      </template>

      <el-table 
        :data="templates" 
        v-loading="loading"
        stripe
      >
        <el-table-column prop="id" label="ID" width="40" />
        <el-table-column prop="template_name" label="模板名称" min-width="300" />
        <el-table-column prop="industry" label="行业" width="120">
          <template #default="{ row }">
            <el-tag>{{ row.industry || '未分类' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="规则数量" width="120">
          <template #default="{ row }">
            {{ (row.parse_rules?.length || 0) + (row.stat_rules?.length || 0) + (row.reply_rules?.length || 0) }}
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="250" show-overflow-tooltip />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="viewTemplate(row)">查看</el-button>
            <el-button link type="primary" size="small" @click="showTemplateDialog('edit', row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="deleteTemplate(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="loadTemplates"
        @current-change="loadTemplates"
        style="margin-top: 20px; justify-content: flex-end"
      />
    </el-card>

    <!-- 导入规则对话框 -->
    <el-dialog v-model="showImportDialog" title="导入规则" width="600px">
      <el-upload
        drag
        :auto-upload="false"
        :on-change="handleFileChange"
        :limit="1"
        accept=".txt,.csv,.md,.json"
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          拖拽文件到此处或 <em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 txt、csv、md、json 格式文件
          </div>
        </template>
      </el-upload>

      <div v-if="importFile" style="margin-top: 20px;">
        <el-alert
          :title="`已选择文件: ${importFile.name}`"
          type="info"
          :closable="false"
        />
        <el-button 
          type="primary" 
          style="margin-top: 15px; width: 100%"
          @click="handleUploadFile"
          :loading="uploading"
        >
          开始导入
        </el-button>
      </div>
    </el-dialog>

    <!-- 模板编辑对话框 -->
    <el-dialog 
      v-model="showTemplateEditDialog" 
      :title="templateDialogTitle" 
      width="800px"
    >
      <el-form :model="currentTemplate" label-width="100px">
        <el-form-item label="模板名称" required>
          <el-input v-model="currentTemplate.template_name" placeholder="请输入模板名称" />
        </el-form-item>
        <el-form-item label="所属行业" required>
          <el-input v-model="currentTemplate.industry" placeholder="例如：电商、餐饮" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input 
            v-model="currentTemplate.description" 
            type="textarea" 
            :rows="3"
            placeholder="模板描述"
          />
        </el-form-item>
        <el-form-item label="解析规则">
          <el-input 
            v-model="currentTemplate.parseRulesText" 
            type="textarea" 
            :rows="5"
            placeholder="JSON格式的解析规则数组"
          />
        </el-form-item>
        <el-form-item label="统计规则">
          <el-input 
            v-model="currentTemplate.statRulesText" 
            type="textarea" 
            :rows="5"
            placeholder="JSON格式的统计规则数组"
          />
        </el-form-item>
        <el-form-item label="回复规则">
          <el-input 
            v-model="currentTemplate.replyRulesText" 
            type="textarea" 
            :rows="5"
            placeholder="JSON格式的回复规则数组"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showTemplateEditDialog = false">取消</el-button>
        <el-button type="primary" @click="saveTemplate" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 查看模板对话框 -->
    <el-dialog v-model="showViewDialog" title="查看规则模板" width="1000px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="模板名称">{{ viewTemplateData.template_name }}</el-descriptions-item>
        <el-descriptions-item label="行业">{{ viewTemplateData.industry || '未分类' }}</el-descriptions-item>
        <el-descriptions-item label="版本">{{ viewTemplateData.version }}</el-descriptions-item>
        <el-descriptions-item label="下载次数">{{ viewTemplateData.download_count }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDate(viewTemplateData.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="作者">{{ viewTemplateData.author_name }}</el-descriptions-item>
        <el-descriptions-item label="描述" :span="2">{{ viewTemplateData.description || '无' }}</el-descriptions-item>
      </el-descriptions>
      
      <el-tabs v-model="activeRuleTab" style="margin-top: 20px;">
        <!-- 解析规则 -->
        <el-tab-pane label="解析规则" name="parse">
          <div class="rule-section">
            <div class="section-header">
              <h4>📋 解析规则说明</h4>
              <el-tag type="info">共 {{ viewTemplateData.parse_rules?.length || 0 }} 条规则</el-tag>
            </div>
            <el-alert 
              title="解析规则用于从消息中提取订单信息，如商品名称、数量、单位等" 
              type="info" 
              :closable="false"
              style="margin-bottom: 15px"
            />
            
            <el-table :data="viewTemplateData.parse_rules || []" border stripe max-height="400">
              <el-table-column prop="rule_name" label="规则名称" width="150" />
              <el-table-column label="匹配方式" width="120">
                <template #default="{ row }">
                  <el-tag size="small" :type="getRuleTypeColor(row.rule_type)">
                    {{ getRuleTypeLabel(row.rule_type) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="pattern" label="匹配内容" min-width="200" show-overflow-tooltip />
              <el-table-column label="提取字段" min-width="150">
                <template #default="{ row }">
                  <span v-if="row.extract_fields">{{ formatExtractFields(row.extract_fields) }}</span>
                  <span v-else>-</span>
                </template>
              </el-table-column>
              <el-table-column prop="priority" label="优先级" width="80" />
              <el-table-column label="状态" width="80">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.is_active ? 'success' : 'info'">
                    {{ row.is_active ? '启用' : '禁用' }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>

        <!-- 统计规则 -->
        <el-tab-pane label="统计规则" name="stat">
          <div class="rule-section">
            <div class="section-header">
              <h4>📊 统计规则说明</h4>
              <el-tag type="info">共 {{ viewTemplateData.stat_rules?.length || 0 }} 条规则</el-tag>
            </div>
            <el-alert 
              title="统计规则定义如何汇总订单数据，如按日/周/月统计，按商品或客户维度等" 
              type="success" 
              :closable="false"
              style="margin-bottom: 15px"
            />
            
            <el-table :data="viewTemplateData.stat_rules || []" border stripe max-height="400">
              <el-table-column prop="rule_name" label="规则名称" width="150" />
              <el-table-column label="统计周期" width="100">
                <template #default="{ row }">
                  {{ getStatTypeLabel(row.stat_type) }}
                </template>
              </el-table-column>
              <el-table-column label="统计维度" min-width="200">
                <template #default="{ row }">
                  <span v-if="row.dimensions">{{ formatDimensions(row.dimensions) }}</span>
                  <span v-else>-</span>
                </template>
              </el-table-column>
              <el-table-column label="图表类型" width="100">
                <template #default="{ row }">
                  <el-tag size="small">{{ getChartTypeLabel(row.chart_type) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="刷新频率" width="100">
                <template #default="{ row }">
                  {{ formatInterval(row.refresh_interval) }}
                </template>
              </el-table-column>
              <el-table-column label="状态" width="80">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.is_active ? 'success' : 'info'">
                    {{ row.is_active ? '启用' : '禁用' }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>

        <!-- 回复规则 -->
        <el-tab-pane label="回复规则" name="reply">
          <div class="rule-section">
            <div class="section-header">
              <h4>💬 回复规则说明</h4>
              <el-tag type="info">共 {{ viewTemplateData.reply_rules?.length || 0 }} 条规则</el-tag>
            </div>
            <el-alert 
              title="回复规则定义机器人如何自动回复消息，当收到特定关键词时自动发送预设内容" 
              type="warning" 
              :closable="false"
              style="margin-bottom: 15px"
            />
            
            <el-table :data="viewTemplateData.reply_rules || []" border stripe max-height="400">
              <el-table-column prop="rule_name" label="规则名称" width="150" />
              <el-table-column label="触发条件" width="120">
                <template #default="{ row }">
                  <el-tag size="small">{{ getTriggerTypeLabel(row.trigger_type) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="trigger_content" label="触发内容" min-width="150" show-overflow-tooltip />
              <el-table-column label="回复内容" min-width="200" show-overflow-tooltip>
                <template #default="{ row }">
                  {{ row.reply_content }}
                </template>
              </el-table-column>
              <el-table-column prop="priority" label="优先级" width="80" />
              <el-table-column label="状态" width="80">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.is_active ? 'success' : 'info'">
                    {{ row.is_active ? '启用' : '禁用' }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
      
      <template #footer>
        <el-button @click="showViewDialog = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Upload, Download, Search, UploadFilled } from '@element-plus/icons-vue'
import {
  getRuleTemplates,
  createRuleTemplate,
  updateRuleTemplate,
  deleteRuleTemplate,
  exportRules
} from '@/api/admin/rules'
import dayjs from 'dayjs'

// 数据
const templates = ref([])
const loading = ref(false)
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 导入相关
const showImportDialog = ref(false)
const importFile = ref(null)
const uploading = ref(false)

// 模板编辑
const showTemplateEditDialog = ref(false)
const templateDialogTitle = ref('')
const saving = ref(false)
const currentTemplate = reactive({
  id: null,
  template_name: '',
  industry: '',
  description: '',
  parseRulesText: '[]',
  statRulesText: '[]',
  replyRulesText: '[]'
})

// 查看模板
const showViewDialog = ref(false)
const viewTemplateData = ref({})
const activeRuleTab = ref('parse')

// 加载模板列表
const loadTemplates = async () => {
  loading.value = true
  try {
    const res = await getRuleTemplates({
      page: currentPage.value,
      per_page: pageSize.value,
      keyword: searchKeyword.value
    })
    
    if (res.success) {
      templates.value = res.templates || []
      total.value = res.total || 0
    } else {
      ElMessage.error(res.message || '加载失败')
    }
  } catch (error) {
    ElMessage.error('加载失败：' + error.message)
  } finally {
    loading.value = false
  }
}

// 显示模板对话框
const showTemplateDialog = (mode, template = null) => {
  if (mode === 'create') {
    templateDialogTitle.value = '新建规则模板'
    Object.assign(currentTemplate, {
      id: null,
      template_name: '',
      industry: '',
      description: '',
      parseRulesText: '[]',
      statRulesText: '[]',
      replyRulesText: '[]'
    })
  } else {
    templateDialogTitle.value = '编辑规则模板'
    Object.assign(currentTemplate, {
      id: template.id,
      template_name: template.template_name,
      industry: template.industry,
      description: template.description || '',
      parseRulesText: JSON.stringify(template.parse_rules || [], null, 2),
      statRulesText: JSON.stringify(template.stat_rules || [], null, 2),
      replyRulesText: JSON.stringify(template.reply_rules || [], null, 2)
    })
  }
  showTemplateEditDialog.value = true
}

// 保存模板
const saveTemplate = async () => {
  if (!currentTemplate.template_name || !currentTemplate.industry) {
    ElMessage.warning('请填写必填字段')
    return
  }

  saving.value = true
  try {
    let parseRules = [], statRules = [], replyRules = []
    try {
      parseRules = JSON.parse(currentTemplate.parseRulesText)
      statRules = JSON.parse(currentTemplate.statRulesText)
      replyRules = JSON.parse(currentTemplate.replyRulesText)
    } catch (e) {
      ElMessage.error('规则内容必须是有效的JSON格式')
      return
    }

    const data = {
      template_name: currentTemplate.template_name,
      industry: currentTemplate.industry,
      description: currentTemplate.description,
      parse_rules: parseRules,
      stat_rules: statRules,
      reply_rules: replyRules
    }

    let res
    if (currentTemplate.id) {
      res = await updateRuleTemplate(currentTemplate.id, data)
    } else {
      res = await createRuleTemplate(data)
    }

    if (res.success) {
      ElMessage.success(currentTemplate.id ? '更新成功' : '创建成功')
      showTemplateEditDialog.value = false
      loadTemplates()
    } else {
      ElMessage.error(res.message || '保存失败')
    }
  } catch (error) {
    ElMessage.error('保存失败：' + error.message)
  } finally {
    saving.value = false
  }
}

// 删除模板
const deleteTemplate = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除这个模板吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    const res = await deleteRuleTemplate(id)
    if (res.success) {
      ElMessage.success('删除成功')
      loadTemplates()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败：' + error.message)
    }
  }
}

// 查看模板
const viewTemplate = (template) => {
  viewTemplateData.value = template
  showViewDialog.value = true
}

// 文件选择
const handleFileChange = (file) => {
  importFile.value = file.raw
}

// 上传文件
const handleUploadFile = async () => {
  if (!importFile.value) {
    ElMessage.warning('请选择文件')
    return
  }

  uploading.value = true
  try {
    // TODO: 实现文件上传逻辑
    ElMessage.info('文件上传功能待实现')
    showImportDialog.value = false
    importFile.value = null
  } catch (error) {
    ElMessage.error('上传失败：' + error.message)
  } finally {
    uploading.value = false
  }
}

// 导出规则
const handleExportRules = async () => {
  try {
    const res = await exportRules({
      format: 'json'
    })
    
    // 创建下载链接
    const blob = new Blob([res], { type: 'application/json' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `rules_export_${dayjs().format('YYYYMMDD_HHmmss')}.json`
    link.click()
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败：' + error.message)
  }
}

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return dayjs(dateStr).format('YYYY-MM-DD HH:mm:ss')
}

// 格式化JSON
const formatJson = (jsonStr) => {
  if (!jsonStr) return ''
  try {
    return JSON.stringify(JSON.parse(jsonStr), null, 2)
  } catch {
    return jsonStr
  }
}

// 解析规则类型标签
const getRuleTypeLabel = (type) => {
  const labels = {
    regex: '正则表达式',
    keyword: '关键词',
    custom: '自定义'
  }
  return labels[type] || type
}

const getRuleTypeColor = (type) => {
  const colors = {
    regex: 'danger',
    keyword: 'primary',
    custom: 'warning'
  }
  return colors[type] || ''
}

// 格式化提取字段
const formatExtractFields = (fields) => {
  if (!fields) return '-'
  try {
    const parsed = typeof fields === 'string' ? JSON.parse(fields) : fields
    if (Array.isArray(parsed)) {
      return parsed.join('、')
    }
    return Object.keys(parsed).join('、')
  } catch {
    return fields
  }
}

// 统计类型标签
const getStatTypeLabel = (type) => {
  const labels = {
    daily: '日报',
    weekly: '周报',
    monthly: '月报',
    custom: '自定义'
  }
  return labels[type] || type
}

// 格式化统计维度
const formatDimensions = (dimensions) => {
  if (!dimensions) return '-'
  try {
    const parsed = typeof dimensions === 'string' ? JSON.parse(dimensions) : dimensions
    if (Array.isArray(parsed)) {
      return parsed.join('、')
    }
    return String(parsed)
  } catch {
    return dimensions
  }
}

// 图表类型标签
const getChartTypeLabel = (type) => {
  const labels = {
    bar: '柱状图',
    line: '折线图',
    pie: '饼图',
    table: '表格'
  }
  return labels[type] || type
}

// 格式化刷新间隔
const formatInterval = (seconds) => {
  if (!seconds) return '-'
  if (seconds < 60) return `${seconds}秒`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟`
  return `${Math.floor(seconds / 3600)}小时`
}

// 触发类型标签
const getTriggerTypeLabel = (type) => {
  const labels = {
    keyword: '关键词',
    pattern: '正则匹配',
    all: '所有消息'
  }
  return labels[type] || type
}

onMounted(() => {
  loadTemplates()
})
</script>

<style scoped>
.rules-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.rule-content {
  background-color: #f5f7fa;
  padding: 15px;
  border-radius: 4px;
  max-height: 400px;
  overflow-y: auto;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.rule-section {
  margin-top: 10px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.section-header h4 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}
</style>

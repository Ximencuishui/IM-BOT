<template>
  <div class="rules-page">
    <el-tabs v-model="activeTab" type="border-card">
      <!-- 解析规则 -->
      <el-tab-pane label="解析规则" name="parse">
        <div class="tab-content">
          <div class="toolbar">
            <el-button type="primary" @click="showParseRuleDialog">
              <el-icon><Plus /></el-icon>
              新增规则
            </el-button>
            <el-button type="success" @click="showImportDialog">
              <el-icon><Upload /></el-icon>
              导入规则
            </el-button>
            <el-button type="warning" @click="showTemplateDialog">
              <el-icon><Collection /></el-icon>
              应用模板
            </el-button>
            <el-button type="info" @click="showCloudDownloadDialog">
              <el-icon><Download /></el-icon>
              从云端下载
            </el-button>
          </div>

          <el-table v-loading="parseRulesLoading" :data="parseRules" border>
            <el-table-column prop="rule_name" label="规则名称" min-width="150" />
            <el-table-column prop="rule_type" label="类型" width="100">
              <template #default="{ row }">
                <el-tag>{{ row.rule_type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="pattern" label="匹配模式" min-width="200" show-overflow-tooltip />
            <el-table-column prop="priority" label="优先级" width="100" />
            <el-table-column prop="is_active" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'info'">
                  {{ row.is_active ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="editParseRule(row)">编辑</el-button>
                <el-button link type="success" size="small" @click="handleTestParseRule(row)">测试</el-button>
                <el-button link type="danger" size="small" @click="handleDeleteParseRule(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- 统计规则 -->
      <el-tab-pane label="统计规则" name="stat">
        <div class="tab-content">
          <div class="toolbar">
            <el-button type="primary" @click="showStatRuleDialog">
              <el-icon><Plus /></el-icon>
              新增规则
            </el-button>
          </div>

          <el-table v-loading="statRulesLoading" :data="statRules" border>
            <el-table-column prop="rule_name" label="规则名称" min-width="150" />
            <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
            <el-table-column prop="priority" label="优先级" width="100" />
            <el-table-column prop="is_active" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'info'">
                  {{ row.is_active ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="editStatRule(row)">编辑</el-button>
                <el-button link type="danger" size="small" @click="handleDeleteStatRule(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 统计规则对话框 -->
    <el-dialog v-model="statRuleDialogVisible" :title="isEditStatRule ? '编辑统计规则' : '新增统计规则'" width="600px">
      <el-form ref="statRuleFormRef" :model="statRuleForm" :rules="statRuleRules" label-width="100px">
        <el-form-item label="规则名称" prop="rule_name">
          <el-input v-model="statRuleForm.rule_name" placeholder="请输入规则名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="statRuleForm.description" type="textarea" :rows="3" placeholder="请输入规则描述" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-input-number v-model="statRuleForm.priority" :min="0" :max="100" style="width: 100%" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="statRuleForm.is_active" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="statRuleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitStatRule" :loading="statRuleSubmitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 解析规则对话框 -->
    <el-dialog v-model="parseRuleDialogVisible" :title="isEditParseRule ? '编辑解析规则' : '新增解析规则'" width="700px">
      <el-form ref="parseRuleFormRef" :model="parseRuleForm" :rules="parseRuleRules" label-width="120px">
        <el-form-item label="规则名称" prop="rule_name">
          <el-input v-model="parseRuleForm.rule_name" placeholder="请输入规则名称" />
        </el-form-item>
        <el-form-item label="规则类型" prop="rule_type">
          <el-select v-model="parseRuleForm.rule_type" placeholder="请选择类型" style="width: 100%">
            <el-option label="正则表达式" value="regex" />
            <el-option label="关键词" value="keyword" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="匹配模式" prop="pattern">
          <el-input v-model="parseRuleForm.pattern" type="textarea" :rows="3" placeholder="输入正则表达式或关键词" />
        </el-form-item>
        <el-form-item label="提取字段">
          <el-input v-model="parseRuleForm.extract_fields" type="textarea" :rows="3" placeholder='JSON格式，例如：{"quantity": 1, "product": 2}' />
        </el-form-item>
        <el-form-item label="优先级">
          <el-input-number v-model="parseRuleForm.priority" :min="0" :max="100" style="width: 100%" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="parseRuleForm.description" type="textarea" :rows="2" placeholder="规则描述" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="parseRuleForm.is_active" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="parseRuleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitParseRule" :loading="parseRuleSubmitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 测试解析规则对话框 -->
    <el-dialog v-model="testDialogVisible" title="测试解析规则" width="600px">
      <el-form label-width="100px">
        <el-form-item label="测试文本">
          <el-input v-model="testText" type="textarea" :rows="4" placeholder="输入测试文本" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="runTest" :loading="testing">运行测试</el-button>
        </el-form-item>
        <el-form-item label="测试结果">
          <el-input v-model="testResult" type="textarea" :rows="6" readonly />
        </el-form-item>
      </el-form>
    </el-dialog>

    <!-- 导入规则对话框 -->
    <el-dialog v-model="importDialogVisible" title="导入规则" width="500px">
      <el-upload
        drag
        :auto-upload="false"
        :on-change="handleFileChange"
        :limit="1"
        accept=".csv,.txt,.md"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">将文件拖到此处，或<em>点击上传</em></div>
        <template #tip>
          <div class="el-upload__tip">支持 CSV、TXT、Markdown 格式</div>
        </template>
      </el-upload>
      <el-form style="margin-top: 20px">
        <el-form-item label="冲突策略">
          <el-radio-group v-model="importConflictStrategy">
            <el-radio label="skip">跳过</el-radio>
            <el-radio label="overwrite">覆盖</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleImport" :loading="importing" :disabled="!importFile">开始导入</el-button>
      </template>
    </el-dialog>

    <!-- 规则模板对话框（本地） -->
    <el-dialog v-model="templateDialogVisible" title="规则模板（本地）" width="700px">
      <el-table v-loading="templatesLoading" :data="templates" border>
        <el-table-column prop="template_name" label="模板名称" min-width="150" />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="rule_count" label="规则数" width="100" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleApplyTemplate(row)">应用</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 从云端下载规则对话框 -->
    <el-dialog v-model="cloudDownloadDialogVisible" title="从云端下载规则模板" width="900px">
      <div class="cloud-download-content">
        <div class="filter-bar">
          <el-select v-model="cloudIndustryFilter" placeholder="行业筛选" clearable style="width: 200px">
            <el-option label="全部行业" value="" />
            <el-option v-for="ind in industries" :key="ind" :label="ind" :value="ind" />
          </el-select>
          <el-button type="primary" @click="loadCloudTemplates">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>

        <el-table v-loading="cloudTemplatesLoading" :data="cloudTemplates" border>
          <el-table-column prop="template_name" label="模板名称" min-width="180" />
          <el-table-column prop="industry" label="行业" width="120">
            <template #default="{ row }">
              <el-tag size="small">{{ row.industry || '通用' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="source_type" label="来源" width="100">
            <template #default="{ row }">
              <el-tag :type="row.source_type === 'official' ? 'success' : 'info'" size="small">
                {{ row.source_type === 'official' ? '官方' : '用户' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="viewCloudTemplate(row)">查看</el-button>
              <el-button link type="success" size="small" @click="downloadCloudTemplate(row)">
                <el-icon><Download /></el-icon>
                下载
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <template #footer>
        <el-button @click="cloudDownloadDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 查看云端模板详情对话框 -->
    <el-dialog v-model="cloudTemplateDetailVisible" :title="currentCloudTemplate?.template_name || '模板详情'" width="800px">
      <div v-if="currentCloudTemplate">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="模板名称">{{ currentCloudTemplate.template_name }}</el-descriptions-item>
          <el-descriptions-item label="行业">{{ currentCloudTemplate.industry || '通用' }}</el-descriptions-item>
          <el-descriptions-item label="来源">
            <el-tag :type="currentCloudTemplate.source_type === 'official' ? 'success' : 'info'" size="small">
              {{ currentCloudTemplate.source_type === 'official' ? '官方' : '用户' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="规则数">{{ currentCloudTemplate.rule_count || 0 }}</el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">{{ currentCloudTemplate.description || '-' }}</el-descriptions-item>
        </el-descriptions>

        <div class="template-rules" v-if="currentCloudTemplate.parse_rules?.length">
          <h4>解析规则预览</h4>
          <el-table :data="currentCloudTemplate.parse_rules" border size="small" max-height="300">
            <el-table-column prop="rule_name" label="规则名称" min-width="150" />
            <el-table-column prop="pattern" label="匹配模式" min-width="200" show-overflow-tooltip />
            <el-table-column prop="priority" label="优先级" width="100" />
          </el-table>
        </div>
      </div>

      <template #footer>
        <el-button @click="cloudTemplateDetailVisible = false">关闭</el-button>
        <el-button type="primary" @click="downloadCurrentCloudTemplate">
          <el-icon><Download /></el-icon>
          下载并应用
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getParseRules, createParseRule, updateParseRule, deleteParseRule, testParseRule, importRules, getRuleTemplates, applyTemplate, getStatRules, createStatRule, updateStatRule, deleteStatRule } from '../../../api/desktop/rules'
import request from '../../../utils/request'

const activeTab = ref('parse')

// 解析规则
const parseRulesLoading = ref(false)
const parseRules = ref([])
const parseRuleDialogVisible = ref(false)
const isEditParseRule = ref(false)
const parseRuleSubmitting = ref(false)
const parseRuleFormRef = ref(null)

const testDialogVisible = ref(false)
const testText = ref('')
const testResult = ref('')
const testing = ref(false)
const currentTestRuleId = ref(null)

const importDialogVisible = ref(false)
const importFile = ref(null)
const importConflictStrategy = ref('skip')
const importing = ref(false)

const templateDialogVisible = ref(false)
const templatesLoading = ref(false)
const templates = ref([])

// 云端下载相关
const cloudDownloadDialogVisible = ref(false)
const cloudTemplatesLoading = ref(false)
const cloudTemplates = ref([])
const cloudIndustryFilter = ref('')
const industries = ref([])
const cloudTemplateDetailVisible = ref(false)
const currentCloudTemplate = ref(null)

const parseRuleForm = reactive({
  id: null,
  rule_name: '',
  rule_type: 'regex',
  pattern: '',
  extract_fields: '',
  priority: 50,
  description: '',
  is_active: true
})

const parseRuleRules = {
  rule_name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  rule_type: [{ required: true, message: '请选择规则类型', trigger: 'change' }],
  pattern: [{ required: true, message: '请输入匹配模式', trigger: 'blur' }]
}

// 统计规则
const statRulesLoading = ref(false)
const statRules = ref([])
const statRuleDialogVisible = ref(false)
const isEditStatRule = ref(false)
const statRuleSubmitting = ref(false)
const statRuleFormRef = ref(null)

const statRuleForm = reactive({
  id: null,
  rule_name: '',
  description: '',
  priority: 50,
  is_active: true
})

const statRuleRules = {
  rule_name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }]
}

// 加载解析规则
const loadParseRules = async () => {
  parseRulesLoading.value = true
  try {
    const res = await getParseRules()
    if (res.success) {
      parseRules.value = res.rules || []
    }
  } catch (error) {
    ElMessage.error('加载解析规则失败')
  } finally {
    parseRulesLoading.value = false
  }
}

// 加载统计规则
const loadStatRules = async () => {
  statRulesLoading.value = true
  try {
    const res = await getStatRules()
    if (res.success) {
      statRules.value = res.rules || []
    }
  } catch (error) {
    ElMessage.error('加载统计规则失败')
  } finally {
    statRulesLoading.value = false
  }
}

// 显示解析规则对话框
const showParseRuleDialog = () => {
  isEditParseRule.value = false
  Object.assign(parseRuleForm, {
    id: null,
    rule_name: '',
    rule_type: 'regex',
    pattern: '',
    extract_fields: '',
    priority: 50,
    description: '',
    is_active: true
  })
  parseRuleDialogVisible.value = true
}

// 编辑解析规则
const editParseRule = (rule) => {
  isEditParseRule.value = true
  Object.assign(parseRuleForm, rule)
  parseRuleDialogVisible.value = true
}

// 提交解析规则
const submitParseRule = async () => {
  if (!parseRuleFormRef.value) return
  
  await parseRuleFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    parseRuleSubmitting.value = true
    try {
      if (isEditParseRule.value) {
        await updateParseRule(parseRuleForm.id, parseRuleForm)
        ElMessage.success('更新成功')
      } else {
        await createParseRule(parseRuleForm)
        ElMessage.success('创建成功')
      }
      parseRuleDialogVisible.value = false
      loadParseRules()
    } catch (error) {
      ElMessage.error('操作失败')
    } finally {
      parseRuleSubmitting.value = false
    }
  })
}

// 测试解析规则
const handleTestParseRule = (rule) => {
  currentTestRuleId.value = rule.id
  testText.value = ''
  testResult.value = ''
  testDialogVisible.value = true
}

// 运行测试
const runTest = async () => {
  if (!testText.value) {
    ElMessage.warning('请输入测试文本')
    return
  }
  
  testing.value = true
  try {
    const res = await testParseRule(currentTestRuleId.value, testText.value)
    if (res.success) {
      testResult.value = JSON.stringify(res.result, null, 2)
    } else {
      testResult.value = '测试失败: ' + (res.error || '未知错误')
    }
  } catch (error) {
    testResult.value = '测试异常: ' + error.message
  } finally {
    testing.value = false
  }
}

// 删除解析规则
const handleDeleteParseRule = (rule) => {
  ElMessageBox.confirm('确定要删除该规则吗?', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await deleteParseRule(rule.id)
      ElMessage.success('删除成功')
      loadParseRules()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
}

// 显示导入对话框
const showImportDialog = () => {
  importFile.value = null
  importDialogVisible.value = true
}

// 文件选择
const handleFileChange = (file) => {
  importFile.value = file.raw
}

// 导入规则
const handleImport = async () => {
  if (!importFile.value) {
    ElMessage.warning('请选择文件')
    return
  }
  
  importing.value = true
  try {
    await importRules(importFile.value, { conflictStrategy: importConflictStrategy.value })
    ElMessage.success('导入成功')
    importDialogVisible.value = false
    loadParseRules()
  } catch (error) {
    ElMessage.error('导入失败')
  } finally {
    importing.value = false
  }
}

// 显示模板对话框
const showTemplateDialog = async () => {
  templateDialogVisible.value = true
  await loadTemplates()
}

// 加载模板列表
const loadTemplates = async () => {
  templatesLoading.value = true
  try {
    const res = await getRuleTemplates()
    if (res.success) {
      templates.value = res.templates || []
    }
  } catch (error) {
    ElMessage.error('加载模板失败')
  } finally {
    templatesLoading.value = false
  }
}

// 应用模板
const handleApplyTemplate = async (template) => {
  ElMessageBox.confirm(`确定要应用模板"${template.template_name}"吗?`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await applyTemplate(template.id)
      ElMessage.success('应用成功')
      templateDialogVisible.value = false
      loadParseRules()
    } catch (error) {
      ElMessage.error('应用失败')
    }
  })
}

// 显示云端下载对话框
const showCloudDownloadDialog = async () => {
  cloudDownloadDialogVisible.value = true
  await loadIndustries()
  await loadCloudTemplates()
}

// 加载行业列表
const loadIndustries = async () => {
  try {
    const res = await request.get('/api/rule-templates/industries')
    if (res.success) {
      industries.value = res.industries || []
    }
  } catch (error) {
    console.error('加载行业列表失败:', error)
  }
}

// 加载云端模板列表
const loadCloudTemplates = async () => {
  cloudTemplatesLoading.value = true
  try {
    const params = {}
    if (cloudIndustryFilter.value) {
      params.industry = cloudIndustryFilter.value
    }
    const res = await request.get('/api/rule-templates/', { params })
    if (res.success) {
      cloudTemplates.value = res.templates || []
    }
  } catch (error) {
    ElMessage.error('加载云端模板失败')
  } finally {
    cloudTemplatesLoading.value = false
  }
}

// 查看云端模板详情
const viewCloudTemplate = async (template) => {
  try {
    const res = await request.get(`/api/rule-templates/${template.id}`)
    if (res.success) {
      currentCloudTemplate.value = res.template
      cloudTemplateDetailVisible.value = true
    } else {
      ElMessage.error('获取模板详情失败')
    }
  } catch (error) {
    ElMessage.error('获取模板详情失败')
  }
}

// 下载云端模板
const downloadCloudTemplate = async (template) => {
  ElMessageBox.confirm(`确定要下载模板"${template.template_name}"并应用到本地吗?`, '确认下载', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'info'
  }).then(async () => {
    try {
      const res = await request.post(`/api/rule-templates/${template.id}/download`)
      if (res.success && res.template) {
        const templateData = res.template
        
        // 应用解析规则
        if (templateData.parse_rules && templateData.parse_rules.length > 0) {
          for (const rule of templateData.parse_rules) {
            try {
              await createParseRule({
                rule_name: rule.rule_name,
                rule_type: rule.rule_type || 'regex',
                pattern: rule.pattern,
                extract_fields: rule.extract_fields || '',
                priority: rule.priority || 50,
                description: rule.description || '',
                is_active: true
              })
            } catch (e) {
              console.warn(`规则 "${rule.rule_name}" 已存在或创建失败`, e)
            }
          }
        }
        
        // 应用统计规则
        if (templateData.stat_rules && templateData.stat_rules.length > 0) {
          for (const rule of templateData.stat_rules) {
            try {
              await createStatRule({
                rule_name: rule.rule_name,
                description: rule.description || '',
                priority: rule.priority || 50,
                is_active: true
              })
            } catch (e) {
              console.warn(`统计规则 "${rule.rule_name}" 已存在或创建失败`, e)
            }
          }
        }
        
        ElMessage.success(`模板下载成功！已应用 ${templateData.parse_rules?.length || 0} 条解析规则，${templateData.stat_rules?.length || 0} 条统计规则`)
        cloudDownloadDialogVisible.value = false
        cloudTemplateDetailVisible.value = false
        loadParseRules()
        loadStatRules()
      } else {
        ElMessage.error('下载失败')
      }
    } catch (error) {
      ElMessage.error('下载失败')
    }
  }).catch(() => {})
}

// 从详情对话框下载当前模板
const downloadCurrentCloudTemplate = async () => {
  if (!currentCloudTemplate.value) return
  await downloadCloudTemplate(currentCloudTemplate.value)
}

// 统计规则相关方法
const showStatRuleDialog = () => {
  isEditStatRule.value = false
  Object.assign(statRuleForm, {
    id: null,
    rule_name: '',
    description: '',
    priority: 50,
    is_active: true
  })
  statRuleDialogVisible.value = true
}

const editStatRule = (rule) => {
  isEditStatRule.value = true
  Object.assign(statRuleForm, rule)
  statRuleDialogVisible.value = true
}

const submitStatRule = async () => {
  if (!statRuleFormRef.value) return
  
  await statRuleFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    statRuleSubmitting.value = true
    try {
      if (isEditStatRule.value) {
        await updateStatRule(statRuleForm.id, statRuleForm)
        ElMessage.success('更新成功')
      } else {
        await createStatRule(statRuleForm)
        ElMessage.success('创建成功')
      }
      statRuleDialogVisible.value = false
      loadStatRules()
    } catch (error) {
      ElMessage.error('操作失败')
    } finally {
      statRuleSubmitting.value = false
    }
  })
}

const handleDeleteStatRule = (rule) => {
  ElMessageBox.confirm('确定要删除该统计规则吗?', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    try {
      await deleteStatRule(rule.id)
      ElMessage.success('删除成功')
      loadStatRules()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  })
}

onMounted(() => {
  loadParseRules()
  loadStatRules()
})
</script>

<style scoped lang="scss">
.rules-page {
  .tab-content {
    padding: 20px 0;
    
    .toolbar {
      margin-bottom: 15px;
      display: flex;
      gap: 10px;
    }
  }
  
  .cloud-download-content {
    .filter-bar {
      margin-bottom: 15px;
      display: flex;
      gap: 10px;
      align-items: center;
    }
  }
  
  .template-rules {
    margin-top: 20px;
    
    h4 {
      margin-bottom: 10px;
      color: #303133;
    }
  }
}
</style>

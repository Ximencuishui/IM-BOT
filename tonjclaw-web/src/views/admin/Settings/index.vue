<template>
  <div class="settings-container">
    <el-tabs v-model="activeTab" type="border-card">
      <!-- 基础设置 -->
      <el-tab-pane label="基础设置" name="basic">
        <el-card>
          <el-form :model="systemParams" label-width="150px">
            <el-form-item label="系统名称">
              <el-input v-model="systemParams.app_name" placeholder="请输入系统名称" />
            </el-form-item>
            <el-form-item label="系统版本">
              <el-input v-model="systemParams.app_version" disabled />
            </el-form-item>
            <el-form-item label="维护模式">
              <el-switch v-model="systemParams.maintenance_mode" />
            </el-form-item>
            <el-form-item label="允许注册">
              <el-switch v-model="systemParams.allow_registration" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveSystemParams">保存设置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- 邮件配置 -->
      <el-tab-pane label="邮件配置" name="email">
        <el-card>
          <el-form :model="emailConfig" label-width="150px">
            <el-form-item label="SMTP服务器">
              <el-input v-model="emailConfig.smtp_host" placeholder="smtp.example.com" />
            </el-form-item>
            <el-form-item label="SMTP端口">
              <el-input-number v-model="emailConfig.smtp_port" :min="1" :max="65535" />
            </el-form-item>
            <el-form-item label="用户名">
              <el-input v-model="emailConfig.smtp_user" placeholder="邮箱地址" />
            </el-form-item>
            <el-form-item label="密码">
              <el-input v-model="emailConfig.smtp_password" type="password" show-password placeholder="授权码或密码" />
            </el-form-item>
            <el-form-item label="发件人邮箱">
              <el-input v-model="emailConfig.from_email" placeholder="noreply@example.com" />
            </el-form-item>
            <el-form-item label="报告接收者">
              <el-input v-model="emailConfig.report_recipients" placeholder="多个邮箱用逗号分隔" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveEmailConfig">保存配置</el-button>
              <el-button @click="showTestEmailDialog = true">测试发送</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- 支付配置 -->
      <el-tab-pane label="支付配置" name="payment">
        <el-tabs v-model="paymentTab">
          <!-- 支付宝 -->
          <el-tab-pane label="支付宝" name="alipay">
            <el-card>
              <el-form :model="alipayConfig" label-width="150px">
                <el-form-item label="App ID">
                  <el-input v-model="alipayConfig.app_id" placeholder="支付宝应用ID" />
                </el-form-item>
                <el-form-item label="应用私钥">
                  <el-input v-model="alipayConfig.private_key" type="textarea" :rows="4" placeholder="应用私钥" />
                </el-form-item>
                <el-form-item label="支付宝公钥">
                  <el-input v-model="alipayConfig.alipay_public_key" type="textarea" :rows="4" placeholder="支付宝公钥" />
                </el-form-item>
                <el-form-item label="网关地址">
                  <el-input v-model="alipayConfig.gateway_url" placeholder="https://openapi.alipay.com/gateway.do" />
                </el-form-item>
                <el-form-item label="回调地址">
                  <el-input v-model="alipayConfig.notify_url" disabled />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="saveAlipayConfig">保存配置</el-button>
                </el-form-item>
              </el-form>
            </el-card>
          </el-tab-pane>

          <!-- 微信支付 -->
          <el-tab-pane label="微信支付" name="wechat">
            <el-card>
              <el-form :model="wechatConfig" label-width="150px">
                <el-form-item label="App ID">
                  <el-input v-model="wechatConfig.app_id" placeholder="微信应用ID" />
                </el-form-item>
                <el-form-item label="商户号">
                  <el-input v-model="wechatConfig.mch_id" placeholder="微信支付商户号" />
                </el-form-item>
                <el-form-item label="API密钥">
                  <el-input v-model="wechatConfig.api_key" type="password" show-password placeholder="API密钥" />
                </el-form-item>
                <el-form-item label="回调地址">
                  <el-input v-model="wechatConfig.notify_url" disabled />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="saveWechatConfig">保存配置</el-button>
                </el-form-item>
              </el-form>
            </el-card>
          </el-tab-pane>
        </el-tabs>
      </el-tab-pane>

      <!-- AI 解析配置 -->
      <el-tab-pane label="AI 解析配置" name="ai_parser">
        <el-card>
          <el-form :model="aiParserConfig" label-width="150px">
            <el-form-item label="启用 AI 解析">
              <el-switch v-model="aiParserConfig.enabled" />
            </el-form-item>
            <el-form-item label="AI 提供商">
              <el-select v-model="aiParserConfig.provider" placeholder="请选择 AI 提供商">
                <el-option label="自定义 HTTP" value="custom_http" />
                <el-option label="HTTP" value="http" />
                <el-option label="模拟模式" value="mock" />
              </el-select>
            </el-form-item>
            <el-form-item label="API 地址">
              <el-input v-model="aiParserConfig.api_url" placeholder="https://example.com/ai/parse" />
            </el-form-item>
            <el-form-item label="API Key">
              <el-input v-model="aiParserConfig.api_key" type="password" show-password placeholder="AI 服务访问密钥" />
            </el-form-item>
            <el-form-item label="模型名称">
              <el-input v-model="aiParserConfig.model" placeholder="例如 gpt-4-1" />
            </el-form-item>
            <el-form-item label="超时时间(秒)">
              <el-input-number v-model="aiParserConfig.timeout" :min="1" :max="120" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="saveAiParserConfig">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- 通知模板 -->
      <el-tab-pane label="通知模板" name="templates">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>通知模板管理</span>
              <el-button type="primary" size="small" @click="showTemplateDialog('create')">
                <el-icon><Plus /></el-icon>新建模板
              </el-button>
            </div>
          </template>

          <el-table :data="templates" border stripe>
            <el-table-column prop="name" label="模板名称" width="200" />
            <el-table-column prop="type" label="类型" width="150">
              <template #default="{ row }">
                <el-tag>{{ getTypeLabel(row.type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="subject" label="主题" show-overflow-tooltip />
            <el-table-column prop="is_active" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.is_active ? 'success' : 'info'">
                  {{ row.is_active ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="previewTemplate(row)">预览</el-button>
                <el-button link type="primary" size="small" @click="showTemplateDialog('edit', row)">编辑</el-button>
                <el-button link type="danger" size="small" @click="deleteTemplate(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 测试邮件对话框 -->
    <el-dialog v-model="showTestEmailDialog" title="测试邮件发送" width="500px">
      <el-form :model="testEmailForm" label-width="100px">
        <el-form-item label="收件人" required>
          <el-input v-model="testEmailForm.to_email" placeholder="请输入测试邮箱" />
        </el-form-item>
        <el-form-item label="主题">
          <el-input v-model="testEmailForm.subject" placeholder="测试邮件主题" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="testEmailForm.body" type="textarea" :rows="4" placeholder="测试邮件内容" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showTestEmailDialog = false">取消</el-button>
        <el-button type="primary" @click="sendTestEmail" :loading="sending">发送</el-button>
      </template>
    </el-dialog>

    <!-- 模板编辑对话框 -->
    <el-dialog v-model="showTemplateEditDialog" :title="templateDialogTitle" width="800px">
      <el-form :model="currentTemplate" label-width="100px">
        <el-form-item label="模板名称" required>
          <el-input v-model="currentTemplate.name" placeholder="例如：续费提醒" />
        </el-form-item>
        <el-form-item label="模板类型" required>
          <el-select v-model="currentTemplate.type" placeholder="请选择类型">
            <el-option label="续费提醒" value="renewal_reminder" />
            <el-option label="到期通知" value="expiration_notice" />
            <el-option label="欢迎邮件" value="welcome_email" />
            <el-option label="密码重置" value="password_reset" />
            <el-option label="订单确认" value="order_confirmation" />
          </el-select>
        </el-form-item>
        <el-form-item label="邮件主题" required>
          <el-input v-model="currentTemplate.subject" placeholder="邮件主题" />
        </el-form-item>
        <el-form-item label="邮件内容" required>
          <el-input 
            v-model="currentTemplate.content" 
            type="textarea" 
            :rows="10" 
            placeholder="支持变量：{user_name}, {product_name}, {expire_date}, {days_left}"
          />
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="currentTemplate.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showTemplateEditDialog = false">取消</el-button>
        <el-button type="primary" @click="saveTemplate">保存</el-button>
      </template>
    </el-dialog>

    <!-- 模板预览对话框 -->
    <el-dialog v-model="showPreviewDialog" title="模板预览" width="800px">
      <div class="preview-content" v-html="previewHtml"></div>
      <template #footer>
        <el-button @click="showPreviewDialog = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import {
  getEmailConfig,
  saveEmailConfig as apiSaveEmailConfig,
  testEmailSend,
  getAlipayConfig,
  saveAlipayConfig as apiSaveAlipayConfig,
  getWechatConfig,
  saveWechatConfig as apiSaveWechatConfig,
  getSystemParams,
  saveSystemParams as apiSaveSystemParams,
  getAiParserConfig,
  saveAiParserConfig as apiSaveAiParserConfig,
  getNotificationTemplates,
  createNotificationTemplate,
  updateNotificationTemplate,
  deleteNotificationTemplate as apiDeleteNotificationTemplate,
  previewNotificationTemplate
} from '@/api/admin/settings'

const activeTab = ref('basic')
const paymentTab = ref('alipay')

// 系统参数
const systemParams = reactive({
  app_name: '',
  app_version: '',
  maintenance_mode: false,
  allow_registration: true
})

// 邮件配置
const emailConfig = reactive({
  smtp_host: '',
  smtp_port: 587,
  smtp_user: '',
  smtp_password: '',
  from_email: '',
  report_recipients: ''
})

// 支付宝配置
const alipayConfig = reactive({
  app_id: '',
  private_key: '',
  alipay_public_key: '',
  gateway_url: 'https://openapi.alipay.com/gateway.do',
  notify_url: ''
})

// 微信支付配置
const wechatConfig = reactive({
  app_id: '',
  mch_id: '',
  api_key: '',
  notify_url: ''
})

// AI 解析配置
const aiParserConfig = reactive({
  enabled: false,
  provider: 'custom_http',
  api_url: '',
  api_key: '',
  model: '',
  timeout: 10
})

// 通知模板
const templates = ref([])
const currentTemplate = reactive({
  id: null,
  name: '',
  type: '',
  subject: '',
  content: '',
  is_active: true
})

// 对话框
const showTestEmailDialog = ref(false)
const showTemplateEditDialog = ref(false)
const showPreviewDialog = ref(false)
const sending = ref(false)
const templateDialogTitle = ref('')
const previewHtml = ref('')

const testEmailForm = reactive({
  to_email: '',
  subject: '测试邮件',
  body: '这是一封测试邮件，用于验证SMTP配置是否正确。'
})

// 加载数据
const loadAllConfigs = async () => {
  await Promise.all([
    loadSystemParams(),
    loadEmailConfig(),
    loadAlipayConfig(),
    loadWechatConfig(),
    loadAiParserConfig(),
    loadNotificationTemplates()
  ])
}

const loadSystemParams = async () => {
  try {
    const res = await getSystemParams()
    if (res.success) {
      Object.assign(systemParams, res.params)
    }
  } catch (error) {
    console.error('加载系统参数失败:', error)
  }
}

const loadEmailConfig = async () => {
  try {
    const res = await getEmailConfig()
    if (res.success) {
      Object.assign(emailConfig, res.config)
    }
  } catch (error) {
    console.error('加载邮件配置失败:', error)
  }
}

const loadAlipayConfig = async () => {
  try {
    const res = await getAlipayConfig()
    if (res.success) {
      Object.assign(alipayConfig, res.config)
    }
  } catch (error) {
    console.error('加载支付宝配置失败:', error)
  }
}

const loadWechatConfig = async () => {
  // TODO: 后端API未实现，暂时跳过
  console.log('微信支付配置功能待实现')
  /*
  try {
    const res = await getWechatConfig()
    if (res.success) {
      Object.assign(wechatConfig, res.config)
    }
  } catch (error) {
    console.error('加载微信配置失败:', error)
  }
  */
}

const loadAiParserConfig = async () => {
  try {
    const res = await getAiParserConfig()
    if (res.success) {
      Object.assign(aiParserConfig, res.config)
    }
  } catch (error) {
    console.error('加载 AI 解析配置失败:', error)
  }
}

const loadNotificationTemplates = async () => {
  try {
    const res = await getNotificationTemplates()
    if (res.success) {
      templates.value = res.templates
    }
  } catch (error) {
    console.error('加载通知模板失败:', error)
  }
}

// 保存系统参数
const saveSystemParams = async () => {
  try {
    const res = await apiSaveSystemParams(systemParams)
    if (res.success) {
      ElMessage.success('系统参数保存成功')
    } else {
      ElMessage.error(res.message || '保存失败')
    }
  } catch (error) {
    ElMessage.error('保存失败：' + error.message)
  }
}

// 保存邮件配置
const saveEmailConfig = async () => {
  try {
    const res = await apiSaveEmailConfig(emailConfig)
    if (res.success) {
      ElMessage.success('邮件配置保存成功')
    } else {
      ElMessage.error(res.message || '保存失败')
    }
  } catch (error) {
    ElMessage.error('保存失败：' + error.message)
  }
}

// 保存支付宝配置
const saveAlipayConfig = async () => {
  try {
    const res = await apiSaveAlipayConfig(alipayConfig)
    if (res.success) {
      ElMessage.success('支付宝配置保存成功')
    } else {
      ElMessage.error(res.message || '保存失败')
    }
  } catch (error) {
    ElMessage.error('保存失败：' + error.message)
  }
}

// 保存微信配置
const saveWechatConfig = async () => {
  ElMessage.warning('微信支付配置功能待实现')
  /*
  try {
    const res = await apiSaveWechatConfig(wechatConfig)
    if (res.success) {
      ElMessage.success('微信支付配置保存成功')
    } else {
      ElMessage.error(res.message || '保存失败')
    }
  } catch (error) {
    ElMessage.error('保存失败：' + error.message)
  }
  */
}

// 保存 AI 解析配置
const saveAiParserConfig = async () => {
  try {
    const res = await apiSaveAiParserConfig(aiParserConfig)
    if (res.success) {
      ElMessage.success('AI 解析配置保存成功')
    } else {
      ElMessage.error(res.message || '保存失败')
    }
  } catch (error) {
    ElMessage.error('保存失败：' + error.message)
  }
}

// 发送测试邮件
const sendTestEmail = async () => {
  if (!testEmailForm.to_email) {
    ElMessage.warning('请输入收件人邮箱')
    return
  }

  sending.value = true
  try {
    const res = await testEmailSend(testEmailForm)
    if (res.success) {
      ElMessage.success('测试邮件发送成功')
      showTestEmailDialog.value = false
    } else {
      ElMessage.error(res.message || '发送失败')
    }
  } catch (error) {
    ElMessage.error('发送失败：' + error.message)
  } finally {
    sending.value = false
  }
}

// 显示模板对话框
const showTemplateDialog = (mode, template = null) => {
  if (mode === 'create') {
    templateDialogTitle.value = '新建通知模板'
    Object.assign(currentTemplate, {
      id: null,
      name: '',
      type: '',
      subject: '',
      content: '',
      is_active: true
    })
  } else {
    templateDialogTitle.value = '编辑通知模板'
    Object.assign(currentTemplate, template)
  }
  showTemplateEditDialog.value = true
}

// 保存模板
const saveTemplate = async () => {
  if (!currentTemplate.name || !currentTemplate.type || !currentTemplate.subject || !currentTemplate.content) {
    ElMessage.warning('请填写所有必填字段')
    return
  }

  try {
    let res
    if (currentTemplate.id) {
      res = await updateNotificationTemplate(currentTemplate.id, currentTemplate)
    } else {
      res = await createNotificationTemplate(currentTemplate)
    }

    if (res.success) {
      ElMessage.success(currentTemplate.id ? '模板更新成功' : '模板创建成功')
      showTemplateEditDialog.value = false
      await loadNotificationTemplates()
    } else {
      ElMessage.error(res.message || '保存失败')
    }
  } catch (error) {
    ElMessage.error('保存失败：' + error.message)
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

    const res = await apiDeleteNotificationTemplate(id)
    if (res.success) {
      ElMessage.success('删除成功')
      await loadNotificationTemplates()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败：' + error.message)
    }
  }
}

// 预览模板
const previewTemplate = async (template) => {
  try {
    const res = await previewNotificationTemplate({
      template_id: template.id,
      variables: {
        user_name: '张三',
        product_name: '高级版',
        expire_date: '2026-05-16',
        days_left: 30
      }
    })

    if (res.success) {
      previewHtml.value = res.preview
      showPreviewDialog.value = true
    } else {
      ElMessage.error(res.message || '预览失败')
    }
  } catch (error) {
    ElMessage.error('预览失败：' + error.message)
  }
}

// 获取类型标签
const getTypeLabel = (type) => {
  const labels = {
    renewal_reminder: '续费提醒',
    expiration_notice: '到期通知',
    welcome_email: '欢迎邮件',
    password_reset: '密码重置',
    order_confirmation: '订单确认'
  }
  return labels[type] || type
}

onMounted(() => {
  loadAllConfigs()
})
</script>

<style scoped>
.settings-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-content {
  max-height: 500px;
  overflow-y: auto;
  padding: 20px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  background-color: #f5f7fa;
}
</style>
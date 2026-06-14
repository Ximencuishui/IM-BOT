<template>
  <div class="affiliates-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>推广管理</h2>
      <el-button type="primary" @click="showAddPromoterDialog = true">
        <el-icon><Plus /></el-icon> 添加推广员
      </el-button>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" style="margin-bottom: 20px;">
      <el-col :span="8">
        <el-card shadow="hover">
          <el-statistic title="推广员总数" :value="stats.total_promoters || 0">
            <template #suffix>
              <el-icon style="vertical-align: -0.125em; margin-left: 4px">
                <User />
              </el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <el-statistic title="活跃推广员" :value="stats.active_promoters || 0" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <el-statistic title="平均佣金比例" :value="stats.avg_commission_rate || 0" suffix="%" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 推广员列表 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>推广员列表</span>
          <el-input
            v-model="searchKeyword"
            placeholder="搜索推广员姓名或编号"
            style="width: 300px"
            clearable
            @clear="loadPromoters"
            @keyup.enter="loadPromoters"
          >
            <template #append>
              <el-button @click="loadPromoters">
                <el-icon><Search /></el-icon>
              </el-button>
            </template>
          </el-input>
        </div>
      </template>

      <el-table :data="promoters" v-loading="loading" stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="promoter_code" label="推广员编号" width="150" />
        <el-table-column prop="promoter_name" label="推广员名称" min-width="150" />
        <el-table-column prop="contact_info" label="联系方式" width="150" show-overflow-tooltip />
        <el-table-column label="佣金比例" width="100">
          <template #default="{ row }">
            <el-tag type="success">{{ row.commission_rate }}%</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="推广链接" min-width="250">
          <template #default="{ row }">
            <div class="promo-link-cell">
              <el-input 
                :value="row.promo_link" 
                size="small" 
                readonly
                style="flex: 1"
              />
              <el-button 
                size="small" 
                type="primary" 
                @click="copyPromoLink(row.promo_link)"
                style="margin-left: 8px"
              >
                复制
              </el-button>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="170">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="editPromoter(row)">编辑</el-button>
            <el-button link type="warning" size="small" @click="regenerateLink(row)">重生成链接</el-button>
            <el-button 
              link 
              :type="row.is_active ? 'warning' : 'success'" 
              size="small" 
              @click="toggleStatus(row)"
            >
              {{ row.is_active ? '禁用' : '启用' }}
            </el-button>
            <el-button link type="danger" size="small" @click="deletePromoter(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="loadPromoters"
        @current-change="loadPromoters"
        style="margin-top: 20px; justify-content: flex-end"
      />
    </el-card>

    <!-- 添加/编辑推广员对话框 -->
    <el-dialog 
      v-model="showAddPromoterDialog" 
      :title="editingPromoter ? '编辑推广员' : '添加推广员'" 
      width="600px"
    >
      <el-form :model="promoterForm" label-width="120px">
        <el-alert
          title="推广链接将自动生成，格式为：系统地址/register?ref=推广员编号"
          type="info"
          :closable="false"
          style="margin-bottom: 20px"
        />
        
        <el-form-item label="推广员名称" required>
          <el-input v-model="promoterForm.promoter_name" placeholder="请输入推广员姓名或公司名称" />
        </el-form-item>
        <el-form-item label="推广员编号">
          <el-input v-model="promoterForm.promoter_code" placeholder="留空则自动生成" />
          <div class="form-tip">唯一标识，用于生成推广链接</div>
        </el-form-item>
        <el-form-item label="联系方式">
          <el-input v-model="promoterForm.contact_info" placeholder="手机/微信/邮箱" />
        </el-form-item>
        <el-form-item label="佣金比例" required>
          <el-input-number 
            v-model="promoterForm.commission_rate" 
            :min="0" 
            :max="100" 
            :precision="2"
            :step="0.5"
            controls-position="right"
          />
          <span class="form-tip">%</span>
        </el-form-item>
        <el-form-item label="备注">
          <el-input 
            v-model="promoterForm.remark" 
            type="textarea" 
            :rows="3"
            placeholder="备注信息"
          />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="promoterForm.is_active" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddPromoterDialog = false">取消</el-button>
        <el-button type="primary" @click="savePromoter" :loading="saving">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, User } from '@element-plus/icons-vue'
import {
  getPromoters,
  createPromoter,
  updatePromoter,
  deletePromoter as apiDeletePromoter,
  regeneratePromoLink,
  getAffiliateStats
} from '@/api/admin/affiliates'
import dayjs from 'dayjs'

// 数据
const promoters = ref([])
const loading = ref(false)
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

// 统计
const stats = reactive({
  total_promoters: 0,
  active_promoters: 0,
  avg_commission_rate: 0
})

// 对话框
const showAddPromoterDialog = ref(false)
const editingPromoter = ref(null)
const saving = ref(false)
const promoterForm = reactive({
  promoter_name: '',
  promoter_code: '',
  contact_info: '',
  commission_rate: 10,
  remark: '',
  is_active: true
})

// 加载推广员列表
const loadPromoters = async () => {
  loading.value = true
  try {
    const res = await getPromoters({
      page: currentPage.value,
      per_page: pageSize.value,
      keyword: searchKeyword.value
    })
    
    if (res.success) {
      promoters.value = res.promoters || []
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

// 加载统计数据
const loadStats = async () => {
  try {
    const res = await getAffiliateStats()
    if (res.success) {
      Object.assign(stats, res.stats)
    }
  } catch (error) {
    console.error('加载统计失败:', error)
  }
}

// 编辑推广员
const editPromoter = (promoter) => {
  editingPromoter.value = promoter
  Object.assign(promoterForm, {
    promoter_name: promoter.promoter_name,
    promoter_code: promoter.promoter_code,
    contact_info: promoter.contact_info || '',
    commission_rate: promoter.commission_rate,
    remark: promoter.remark || '',
    is_active: promoter.is_active
  })
  showAddPromoterDialog.value = true
}

// 保存推广员
const savePromoter = async () => {
  if (!promoterForm.promoter_name) {
    ElMessage.warning('请输入推广员名称')
    return
  }
  if (!promoterForm.commission_rate || promoterForm.commission_rate < 0) {
    ElMessage.warning('请输入有效的佣金比例')
    return
  }

  saving.value = true
  try {
    let res
    if (editingPromoter.value) {
      res = await updatePromoter(editingPromoter.value.id, promoterForm)
    } else {
      res = await createPromoter(promoterForm)
    }

    if (res.success) {
      ElMessage.success(editingPromoter.value ? '更新成功' : '添加成功')
      showAddPromoterDialog.value = false
      editingPromoter.value = null
      resetForm()
      loadPromoters()
      loadStats()
    } else {
      ElMessage.error(res.message || '保存失败')
    }
  } catch (error) {
    ElMessage.error('保存失败：' + error.message)
  } finally {
    saving.value = false
  }
}

// 切换状态
const toggleStatus = async (promoter) => {
  const action = promoter.is_active ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(`确定要${action}该推广员吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    const res = await updatePromoter(promoter.id, {
      is_active: !promoter.is_active
    })

    if (res.success) {
      ElMessage.success(`${action}成功`)
      loadPromoters()
      loadStats()
    } else {
      ElMessage.error(res.message || '操作失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败：' + error.message)
    }
  }
}

// 重新生成推广链接
const regenerateLink = async (promoter) => {
  try {
    await ElMessageBox.confirm('确定要重新生成推广链接吗？原链接将失效。', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    const res = await regeneratePromoLink(promoter.id)
    if (res.success) {
      ElMessage.success('推广链接已重新生成')
      loadPromoters()
    } else {
      ElMessage.error(res.message || '操作失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败：' + error.message)
    }
  }
}

// 删除推广员
const deletePromoter = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除这个推广员吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    const res = await apiDeletePromoter(id)
    if (res.success) {
      ElMessage.success('删除成功')
      loadPromoters()
      loadStats()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败：' + error.message)
    }
  }
}

// 复制推广链接
const copyPromoLink = async (link) => {
  try {
    await navigator.clipboard.writeText(link)
    ElMessage.success('推广链接已复制到剪贴板')
  } catch (error) {
    // 降级方案
    const textarea = document.createElement('textarea')
    textarea.value = link
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    ElMessage.success('推广链接已复制到剪贴板')
  }
}

// 重置表单
const resetForm = () => {
  Object.assign(promoterForm, {
    promoter_name: '',
    promoter_code: '',
    contact_info: '',
    commission_rate: 10,
    remark: '',
    is_active: true
  })
}

// 格式化日期
const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return dayjs(dateStr).format('YYYY-MM-DD HH:mm:ss')
}

onMounted(() => {
  loadPromoters()
  loadStats()
})
</script>

<style scoped>
.affiliates-container {
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

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.promo-link-cell {
  display: flex;
  align-items: center;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}
</style>

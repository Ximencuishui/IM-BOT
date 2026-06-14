<template>
  <div class="user-subscriptions">
    <h2 class="section-title">订阅管理</h2>

    <el-table :data="subscriptions" style="width: 100%" v-loading="loading">
      <el-table-column prop="plan_name" label="套餐名称" width="180"></el-table-column>
      <el-table-column prop="plan_type" label="类型" width="100">
        <template #default="{ row }">
          <el-tag :type="row.plan_type === 'yearly' ? 'success' : 'info'">
            {{ row.plan_type === 'yearly' ? '年付' : '月付' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="price" label="价格" width="120">
        <template #default="{ row }">¥{{ row.price }}</template>
      </el-table-column>
      <el-table-column prop="start_date" label="开始日期" width="120">
        <template #default="{ row }">{{ formatDate(row.start_date) }}</template>
      </el-table-column>
      <el-table-column prop="end_date" label="结束日期" width="120">
        <template #default="{ row }">{{ formatDate(row.end_date) }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'info'">
            {{ row.status === 'active' ? '生效中' : '已过期' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作">
        <template #default="{ row }">
          <el-button v-if="row.status === 'active'" size="small" @click="renewSubscription(row)">续订</el-button>
          <el-button v-else size="small" type="primary" @click="reactivateSubscription(row)">重新激活</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-empty v-if="subscriptions.length === 0 && !loading" description="暂无订阅记录"></el-empty>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../../../utils/request'

const loading = ref(false)
const subscriptions = ref([])

const loadSubscriptions = async () => {
  loading.value = true
  try {
    const res = await request.get('/api/pricing/subscriptions')
    if (res.success) {
      subscriptions.value = res.subscriptions || []
    } else {
      ElMessage.error(res.error || '加载失败')
    }
  } catch (error) {
    console.error('加载订阅列表失败:', error)
  } finally {
    loading.value = false
  }
}

const formatDate = (dateStr) => dateStr ? new Date(dateStr).toLocaleDateString('zh-CN') : '-'

const renewSubscription = (sub) => {
  ElMessage.info('续订功能开发中，请前往授权管理进行批量展期')
}

const reactivateSubscription = (sub) => {
  ElMessage.info('重新激活功能开发中')
}

onMounted(() => {
  loadSubscriptions()
})
</script>

<style scoped lang="scss">
.user-subscriptions {
  .section-title {
    font-size: 20px;
    margin-bottom: 20px;
    color: #1e293b;
  }
}
</style>

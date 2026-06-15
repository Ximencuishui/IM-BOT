﻿﻿﻿<template>
  <div class="users-page">
    <div class="page-header">
      <h2 class="page-title">用户管理</h2>
      <el-button type="primary" @click="showAddDialog">
        <el-icon><Plus /></el-icon>
        添加用户
      </el-button>
    </div>

    <!-- 搜索框 -->
    <el-card class="search-card">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="用户名">
          <el-input v-model="searchForm.username" placeholder="请输入用户名" clearable />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="searchForm.email" placeholder="请输入邮箱" clearable />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="searchForm.role" placeholder="选择角色" clearable>
            <el-option label="超级管理员" value="super_admin" />
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.is_active" placeholder="选择状态" clearable>
            <el-option label="激活" :value="1" />
            <el-option label="禁用" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">搜索</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 用户列表 -->
    <el-card class="table-card">
      <el-table
        :data="users"
        v-loading="loading"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="email" label="邮箱" width="200" />
        <el-table-column prop="phone" label="手机号" width="120" />
        <el-table-column prop="company_name" label="公司" width="150" />
        <el-table-column prop="role" label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="getRoleType(row.role)">
              {{ getRoleText(row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'">
              {{ row.is_active ? '激活' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="subscription_type" label="订阅" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.subscription_type === 'yearly' ? '年付' : '月付' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="220">
          <template #default="{ row }">
            <el-button size="small" @click="handleView(row)">详情</el-button>
            <el-button size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button size="small" type="warning" @click="handleResetPassword(row)">重置密码</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
        style="margin-top: 20px; justify-content: flex-end"
      />
    </el-card>

    <!-- 添加/编辑对话�?-->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      @close="handleDialogClose"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="formData.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="formData.email" placeholder="请输入邮箱" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="密码" prop="password" v-if="!isEdit">
          <el-input v-model="formData.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="formData.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="公司" prop="company_name">
          <el-input v-model="formData.company_name" placeholder="请输入公司名称" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="formData.role" placeholder="请选择角色" style="width: 100%">
            <el-option label="超级管理员" value="super_admin" />
            <el-option label="管理员" value="admin" />
            <el-option label="普通用户" value="user" />
          </el-select>
        </el-form-item>
        <el-form-item label="订阅类型" prop="subscription_type">
          <el-radio-group v-model="formData.subscription_type">
            <el-radio label="monthly">月付</el-radio>
            <el-radio label="yearly">年付</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="状态" prop="is_active">
          <el-switch v-model="formData.is_active" :active-value="1" :inactive-value="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 用户详情对话�?-->
    <el-dialog
      v-model="showDetailDialog"
      title="用户详情"
      width="700px"
    >
      <el-descriptions :column="2" border v-if="userDetail">
        <el-descriptions-item label="ID">{{ userDetail.user.id }}</el-descriptions-item>
        <el-descriptions-item label="用户名">{{ userDetail.user.username || '-' }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">{{ userDetail.user.email }}</el-descriptions-item>
        <el-descriptions-item label="手机号">{{ userDetail.user.phone || '-' }}</el-descriptions-item>
        <el-descriptions-item label="公司">{{ userDetail.user.company_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="角色">
          <el-tag :type="getRoleType(userDetail.user.role)">
            {{ getRoleText(userDetail.user.role) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="订阅类型">
          {{ userDetail.user.subscription_type === 'yearly' ? '年付' : '月付' }}
        </el-descriptions-item>
        <el-descriptions-item label="订阅过期">
          {{ formatDate(userDetail.user.subscription_expires_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="订阅状态">
          <el-tag :type="userDetail.is_subscription_valid ? 'success' : 'danger'">
            {{ userDetail.is_subscription_valid ? '有效' : '已过期' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="最大群数">{{ userDetail.user.max_groups }}</el-descriptions-item>
        <el-descriptions-item label="可用群数">
          <el-tag type="info">{{ userDetail.available_groups }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="授权码总数">{{ userDetail.license_count }}</el-descriptions-item>
        <el-descriptions-item label="活跃授权数">{{ userDetail.active_license_count }}</el-descriptions-item>
        <el-descriptions-item label="团队成员">{{ userDetail.team_member_count }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="userDetail.user.is_active ? 'success' : 'danger'">
            {{ userDetail.user.is_active ? '激活' : '禁用' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="最后登录">{{ formatDate(userDetail.user.last_login_at) }}</el-descriptions-item>
        <el-descriptions-item label="注册时间">{{ formatDate(userDetail.user.created_at) }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="showDetailDialog = false">关闭</el-button>
        <el-button type="primary" @click="handleEditFromDetail">编辑</el-button>
        <el-button type="warning" @click="handleResetPasswordFromDetail">重置密码</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码对话�?-->
    <el-dialog
      v-model="showResetPasswordDialog"
      title="重置密码"
      width="500px"
    >
      <el-alert
        title="注意：重置密码后用户将使用新密码登录"
        type="warning"
        :closable="false"
        style="margin-bottom: 20px"
      />
      <el-form
        ref="resetFormRef"
        :model="resetForm"
        :rules="resetRules"
        label-width="100px"
      >
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="resetForm.new_password" type="password" placeholder="请输入新密码" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input v-model="resetForm.confirm_password" type="password" placeholder="请再次输入新密码" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showResetPasswordDialog = false">取消</el-button>
        <el-button type="primary" @click="submitResetPassword" :loading="resetting">
          确认重置
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getUsers, createUser, updateUser, deleteUser, resetPassword, getUserDetail } from '../../../api/admin/users'
import dayjs from 'dayjs'

const loading = ref(false)
const submitting = ref(false)
const resetting = ref(false)
const users = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)
const resetFormRef = ref(null)

const showDetailDialog = ref(false)
const showResetPasswordDialog = ref(false)
const userDetail = ref(null)
const resettingUserId = ref(null)

const searchForm = reactive({
  username: '',
  email: '',
  role: '',
  is_active: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const formData = reactive({
  id: null,
  username: '',
  email: '',
  password: '',
  phone: '',
  company_name: '',
  role: 'user',
  subscription_type: 'monthly',
  is_active: 1
})

const resetForm = reactive({
  new_password: '',
  confirm_password: ''
})

const formRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 20, message: '长度在2到20个字符', trigger: 'blur' }
  ],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ],
  role: [
    { required: true, message: '请选择角色', trigger: 'change' }
  ]
}

const resetRules = {
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: (rule, value, callback) => {
      if (value !== resetForm.new_password) {
        callback(new Error('两次输入的密码不一致'))
      } else {
        callback()
      }
    }, trigger: 'blur' }
  ]
}

const dialogTitle = ref('添加用户')

const loadUsers = async () => {
  loading.value = true
  try {
    const params = {
      ...searchForm,
      page: pagination.page,
      page_size: pagination.pageSize
    }
    
    const res = await getUsers(params)
    users.value = res.users || []
    pagination.total = res.pagination?.total || 0
  } catch (error) {
    console.error('加载用户列表失败:', error)
    ElMessage.error('加载用户列表失败')
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  loadUsers()
}

const handleReset = () => {
  Object.assign(searchForm, {
    username: '',
    email: '',
    role: '',
    is_active: ''
  })
  handleSearch()
}

const handlePageChange = (page) => {
  pagination.page = page
  loadUsers()
}

const handleSizeChange = (size) => {
  pagination.pageSize = size
  pagination.page = 1
  loadUsers()
}

const showAddDialog = () => {
  isEdit.value = false
  dialogTitle.value = '添加用户'
  resetFormData()
  dialogVisible.value = true
}

const handleView = async (row) => {
  try {
    const res = await getUserDetail(row.id)
    if (res.success) {
      userDetail.value = res
      showDetailDialog.value = true
    }
  } catch (error) {
    ElMessage.error('获取用户详情失败')
  }
}

const handleEdit = (row) => {
  isEdit.value = true
  dialogTitle.value = '编辑用户'
  Object.assign(formData, {
    id: row.id,
    username: row.username,
    email: row.email,
    phone: row.phone || '',
    company_name: row.company_name || '',
    role: row.role,
    subscription_type: row.subscription_type || 'monthly',
    is_active: row.is_active
  })
  dialogVisible.value = true
}

const handleEditFromDetail = () => {
  showDetailDialog.value = false
  if (userDetail.value) {
    handleEdit(userDetail.value.user)
  }
}

const handleDelete = (row) => {
  ElMessageBox.confirm(
    `确定要删除用�?"${row.username}" 吗？`,
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await deleteUser(row.id)
      ElMessage.success('删除成功')
      loadUsers()
    } catch (error) {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

const handleResetPassword = (row) => {
  resettingUserId.value = row.id
  Object.assign(resetForm, {
    new_password: '',
    confirm_password: ''
  })
  showResetPasswordDialog.value = true
}

const handleResetPasswordFromDetail = () => {
  showDetailDialog.value = false
  if (userDetail.value) {
    handleResetPassword(userDetail.value.user)
  }
}

const submitResetPassword = async () => {
  if (!resetFormRef.value) return
  
  await resetFormRef.value.validate(async (valid) => {
    if (valid) {
      resetting.value = true
      try {
        await resetPassword(resettingUserId.value, {
          new_password: resetForm.new_password
        })
        ElMessage.success('密码重置成功')
        showResetPasswordDialog.value = false
      } catch (error) {
        console.error('重置密码失败:', error)
        ElMessage.error('重置密码失败')
      } finally {
        resetting.value = false
      }
    }
  })
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true
      try {
        if (isEdit.value) {
          await updateUser(formData.id, formData)
          ElMessage.success('更新成功')
        } else {
          await createUser(formData)
          ElMessage.success('创建成功')
        }
        dialogVisible.value = false
        loadUsers()
      } catch (error) {
        console.error('提交失败:', error)
        ElMessage.error(isEdit.value ? '更新失败' : '创建失败')
      } finally {
        submitting.value = false
      }
    }
  })
}

const handleDialogClose = () => {
  resetFormData()
  if (formRef.value) {
    formRef.value.clearValidate()
  }
}

const resetFormData = () => {
  Object.assign(formData, {
    id: null,
    username: '',
    email: '',
    password: '',
    phone: '',
    company_name: '',
    role: 'user',
    subscription_type: 'monthly',
    is_active: 1
  })
}

const getRoleText = (role) => {
  const map = {
    super_admin: '超级管理员',
    admin: '管理员',
    user: '普通用户'
  }
  return map[role] || role
}

const getRoleType = (role) => {
  const map = {
    super_admin: 'danger',
    admin: 'warning',
    user: 'info'
  }
  return map[role] || 'info'
}

const formatDate = (date) => {
  return date ? dayjs(date).format('YYYY-MM-DD HH:mm:ss') : '-'
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped lang="scss">
.users-page {
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    
    .page-title {
      font-size: 24px;
      color: #303133;
      margin: 0;
    }
  }
  
  .search-card {
    margin-bottom: 20px;
  }
  
  .table-card {
    ::deep(.el-card__body) {
      padding: 20px;
    }
  }
}
</style>
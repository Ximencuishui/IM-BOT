<template>
  <div class="user-profile">
    <el-card class="box-card">
      <template #header>
        <div class="card-header">
          <span>个人信息</span>
        </div>
      </template>
      <el-form :model="profileForm" label-width="100px" style="max-width: 600px;">
        <el-form-item label="用户名">
          <el-input v-model="profileForm.username" disabled></el-input>
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="profileForm.email" placeholder="用于接收通知"></el-input>
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="profileForm.phone" placeholder="选填"></el-input>
        </el-form-item>
        <el-form-item label="注册时间">
          <el-input :value="profileForm.created_at" disabled></el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleUpdateProfile" :loading="updating">保存修改</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="box-card" style="margin-top: 20px;">
      <template #header>
        <div class="card-header">
          <span>修改密码</span>
        </div>
      </template>
      <el-form :model="passwordForm" label-width="100px" style="max-width: 600px;" :rules="passwordRules" ref="passwordFormRef">
        <el-form-item label="当前密码" prop="old_password">
          <el-input v-model="passwordForm.old_password" type="password" show-password></el-input>
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="passwordForm.new_password" type="password" show-password></el-input>
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input v-model="passwordForm.confirm_password" type="password" show-password></el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="warning" @click="handleChangePassword" :loading="changing">修改密码</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '../../../stores/user'
import request from '../../../utils/request'

const userStore = useUserStore()
const updating = ref(false)
const changing = ref(false)
const passwordFormRef = ref(null)

const profileForm = reactive({
  username: '',
  email: '',
  phone: '',
  created_at: ''
})

const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const validateConfirmPassword = (rule, value, callback) => {
  if (value !== passwordForm.new_password) {
    callback(new Error('两次输入的新密码不一致'))
  } else {
    callback()
  }
}

const passwordRules = {
  old_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [{ required: true, message: '请输入新密码', trigger: 'blur' }, { min: 6, message: '长度至少为6个字符', trigger: 'blur' }],
  confirm_password: [{ required: true, validator: validateConfirmPassword, trigger: 'blur' }]
}

const loadProfile = async () => {
  try {
    const res = await request.get('/api/auth/me')
    if (res.success && res.user) {
      Object.assign(profileForm, {
        username: res.user.username,
        email: res.user.email || '',
        phone: res.user.phone || '',
        created_at: res.user.created_at ? new Date(res.user.created_at).toLocaleDateString('zh-CN') : ''
      })
    }
  } catch (error) {
    console.error('加载用户信息失败:', error)
  }
}

const handleUpdateProfile = async () => {
  updating.value = true
  try {
    const res = await request.put('/api/auth/profile', {
      email: profileForm.email,
      phone: profileForm.phone
    })
    if (res.success) {
      ElMessage.success('个人信息更新成功')
      userStore.setUserInfo({ ...userStore.userInfo, email: profileForm.email, phone: profileForm.phone })
    } else {
      ElMessage.error(res.error || '更新失败')
    }
  } catch (error) {
    ElMessage.error('网络请求失败')
  } finally {
    updating.value = false
  }
}

const handleChangePassword = async () => {
  if (!passwordFormRef.value) return
  await passwordFormRef.value.validate(async (valid) => {
    if (valid) {
      changing.value = true
      try {
        const res = await request.post('/api/auth/change-password', {
          old_password: passwordForm.old_password,
          new_password: passwordForm.new_password
        })
        if (res.success) {
          ElMessage.success('密码修改成功，请重新登录')
          setTimeout(() => {
            userStore.logout()
            window.location.href = '/login'
          }, 1500)
        } else {
          ElMessage.error(res.error || '修改失败')
        }
      } catch (error) {
        ElMessage.error('网络请求失败')
      } finally {
        changing.value = false
      }
    }
  })
}

onMounted(() => {
  loadProfile()
})
</script>

<style scoped lang="scss">
.user-profile {
  .card-header {
    font-weight: bold;
    color: #1e293b;
  }
}
</style>

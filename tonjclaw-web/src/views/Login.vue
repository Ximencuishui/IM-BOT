<template>
  <div class="login-container">
    <el-card class="login-card">
      <template #header>
        <h2>🚀 配送订货系统</h2>
      </template>
      
      <el-form :model="loginForm" :rules="rules" ref="loginFormRef" label-width="0">
        <el-form-item prop="username">
          <el-input
            v-model="loginForm.username"
            placeholder="用户名或邮箱"
            prefix-icon="User"
            size="large"
          />
        </el-form-item>
        
        <el-form-item prop="password">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="密码"
            prefix-icon="Lock"
            size="large"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            style="width: 100%"
            :loading="loading"
            @click="handleLogin"
          >
            登录
          </el-button>
        </el-form-item>
        
        <el-divider>或</el-divider>
        
        <el-form-item>
          <el-button
            type="success"
            size="large"
            style="width: 100%"
            @click="handleBossLogin"
          >
            👔 BOSS快捷登录
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { login } from '../api/auth'
import { ElMessage } from 'element-plus'
import { cacheDemoLicense } from '../utils/demoBossTrial'

const router = useRouter()
const userStore = useUserStore()
const loginFormRef = ref(null)
const loading = ref(false)

const loginForm = reactive({
  username: '',
  password: ''
})

const rules = {
  username: [
    { required: true, message: '请输入用户名或邮箱', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度至少6位', trigger: 'blur' }
  ]
}

const handleLogin = async () => {
  if (!loginFormRef.value) return
  
  await loginFormRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        const res = await login(loginForm)
        
        if (res.success) {
          userStore.setToken(res.token)
          userStore.setUserInfo(res.user)
          
          ElMessage.success('登录成功')
          
          // 根据角色跳转
          if (res.user.role === 'super_admin' || res.user.role === 'admin') {
            router.push('/admin/dashboard')
          } else {
            router.push('/user/dashboard')
          }
        } else {
          ElMessage.error(res.message || '登录失败')
        }
      } catch (error) {
        console.error('登录错误:', error)
      } finally {
        loading.value = false
      }
    }
  })
}

const handleBossLogin = async () => {
  loading.value = true
  try {
    const res = await login({
      username: 'BOSS',
      password: '888888'
    })
    
    if (res.success) {
      userStore.setToken(res.token)
      userStore.setUserInfo(res.user)
      
      if (res.demo_license) {
        cacheDemoLicense(res.demo_license)
        sessionStorage.removeItem('tonjclaw_demo_trial_dialog_shown')
      }
      ElMessage.success('BOSS 账号登录成功，即将进入桌面端')
      router.push('/desktop/orders')
    } else {
      ElMessage.error(res.message || '登录失败')
    }
  } catch (error) {
    console.error('BOSS登录错误:', error)
    ElMessage.error('BOSS账号登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="scss">
.login-container {
  height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 400px;
  
  :deep(.el-card__header) {
    text-align: center;
    padding: 30px 20px 20px;
    
    h2 {
      margin: 0;
      color: #409EFF;
      font-size: 24px;
    }
  }
  
  :deep(.el-card__body) {
    padding: 20px 30px 30px;
  }
}
</style>

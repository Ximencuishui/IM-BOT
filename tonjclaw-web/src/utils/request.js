import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import router from '../router'
import { useUserStore } from '../stores/user'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: false
})

request.defaults.headers.common['Cache-Control'] = 'no-cache'
request.defaults.headers.common['Pragma'] = 'no-cache'

const errorMessageMap = {
  400: '请求参数错误',
  401: '登录已过期，请重新登录',
  403: '权限不足，无法访问',
  404: '请求的资源不存在',
  405: '请求方法不允许',
  408: '请求超时',
  429: '请求过于频繁，请稍后重试',
  500: '服务器内部错误',
  502: '网关错误',
  503: '服务暂不可用',
  504: '网关超时'
}

const getErrorMessage = (status) => {
  return errorMessageMap[status] || '网络请求失败'
}

const handleUnauthorized = () => {
  const userStore = useUserStore()
  userStore.logout()
  ElMessageBox.confirm(
    '登录已过期，是否重新登录？',
    '提示',
    {
      confirmButtonText: '重新登录',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    router.push('/login')
  }).catch(() => {
    router.push('/login')
  })
}

request.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    if (import.meta.env.DEV) {
      console.log('[Request Debug]', {
        baseURL: config.baseURL,
        url: config.url,
        method: config.method,
        fullURL: `${config.baseURL}${config.url}`
      })
    }

    return config
  },
  error => {
    console.error('[Request Error]', error)
    ElMessage.error('请求配置错误')
    return Promise.reject(error)
  }
)

request.interceptors.response.use(
  response => {
    const res = response.data

    if (res && typeof res.success === 'boolean' && !res.success) {
      const errorMsg = res.error || res.message || '操作失败'
      
      if (res.code === 401 || response.status === 401) {
        handleUnauthorized()
        return Promise.reject(new Error(errorMsg))
      }

      if (response.status === 403) {
        ElMessage.warning('权限不足')
        return Promise.reject(new Error(errorMsg))
      }

      ElMessage.error(errorMsg)
      return Promise.reject(new Error(errorMsg))
    }

    return res
  },
  error => {
    console.error('[Response Error]', error)

    if (error.response) {
      const { status, data } = error.response
      
      if (status === 401) {
        handleUnauthorized()
      } else {
        const errorMsg = data?.error || data?.message || getErrorMessage(status)
        ElMessage.error(errorMsg)
      }
    } else if (error.request) {
      if (error.code === 'ECONNABORTED') {
        ElMessage.error('请求超时，请检查网络')
      } else {
        ElMessage.error('网络错误，请检查网络连接')
      }
    } else {
      ElMessage.error('请求配置错误')
    }

    return Promise.reject(error)
  }
)

export default request
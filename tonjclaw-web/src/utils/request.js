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

// 需要重试的请求（幂等请求）
const shouldRetry = (config) => {
  if (!config.retry) return false
  const retryMethods = ['GET', 'HEAD', 'OPTIONS', 'PUT', 'DELETE']
  return retryMethods.includes(config.method?.toUpperCase())
}

request.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }

    // 添加AbortController支持（离开页面时取消请求）
    if (!config.signal && typeof AbortController !== 'undefined') {
      const controller = new AbortController()
      config.signal = controller.signal
      config._abortController = controller
    }

    if (import.meta.env.DEV) {
      console.log('[Request Debug]', {
        url: config.url,
        method: config.method,
        retry: config.retry,
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

// 自动重试拦截器
const retryInterceptor = (error) => {
  const config = error.config

  // 非幂等请求不重试
  if (!config || !shouldRetry(config)) {
    return Promise.reject(error)
  }

  // 初始化重试计数
  config.retryCount = config.retryCount || 0
  const maxRetries = config.retryMax || 2

  // 已达最大重试次数
  if (config.retryCount >= maxRetries) {
    ElMessage.warning(`请求失败，已重试 ${maxRetries} 次`)
    return Promise.reject(error)
  }

  // 增量重试（1s, 2s）
  config.retryCount += 1
  const delay = config.retryDelay || 1000 * config.retryCount

  console.log(`[Retry] ${config.method} ${config.url} (${config.retryCount}/${maxRetries}) 等待${delay}ms`)

  return new Promise(resolve => setTimeout(resolve, delay))
    .then(() => request(config))
}

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
    // 取消的请求不处理
    if (axios.isCancel(error)) {
      return Promise.reject(error)
    }

    console.error('[Response Error]', error)

    if (error.response) {
      const { status, data } = error.response

      if (status === 401) {
        handleUnauthorized()
      } else if (status === 429) {
        ElMessage.warning('请求过于频繁，请稍后重试')
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

    return retryInterceptor(error)
  }
)

export default request
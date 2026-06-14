import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

// 创建 axios 实例
const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  },
  // 开发环境下使用代理，不需要withCredentials
  withCredentials: false
})

// 强制清除可能的缓存干扰
request.defaults.headers.common['Cache-Control'] = 'no-cache'
request.defaults.headers.common['Pragma'] = 'no-cache'

// 请求拦截器
request.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    // 调试日志：打印完整请求URL
    console.log('[Request Debug]', {
      baseURL: config.baseURL,
      url: config.url,
      method: config.method,
      fullURL: `${config.baseURL}${config.url}`
    })
    return config
  },
  error => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  response => {
    const res = response.data
    
    // 处理业务逻辑错误 (假设后端返回 { success: false, error: '...' })
    if (res && typeof res.success === 'boolean' && !res.success) {
      ElMessage.error(res.error || res.message || '操作失败')
      return Promise.reject(new Error(res.error || res.message || '操作失败'))
    }
    
    return res
  },
  error => {
    console.error('响应错误:', error)
    
    if (error.response) {
      switch (error.response.status) {
        case 401:
          ElMessage.error('未授权，请重新登录')
          localStorage.removeItem('token')
          localStorage.removeItem('userInfo')
          router.push('/login')
          break
        case 403:
          ElMessage.error('拒绝访问')
          break
        case 404:
          ElMessage.error('请求的资源不存在')
          break
        case 500:
          ElMessage.error('服务器错误')
          break
        default:
          ElMessage.error(error.response.data?.message || '请求失败')
      }
    } else if (error.request) {
      ElMessage.error('网络错误，请检查网络连接')
    } else {
      ElMessage.error('请求配置错误')
    }
    
    return Promise.reject(error)
  }
)

export default request

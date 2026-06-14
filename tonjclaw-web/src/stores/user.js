import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUserStore = defineStore('user', () => {
  const userInfo = ref(JSON.parse(localStorage.getItem('userInfo') || '{}'))
  const token = ref(localStorage.getItem('token') || '')
  const sidebarCollapsed = ref(false)
  
  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => 
    userInfo.value.role === 'super_admin' || userInfo.value.role === 'admin'
  )
  
  function setToken(newToken) {
    token.value = newToken
    localStorage.setItem('token', newToken)
  }
  
  function setUserInfo(info) {
    userInfo.value = info
    localStorage.setItem('userInfo', JSON.stringify(info))
  }
  
  function logout() {
    token.value = ''
    userInfo.value = {}
    localStorage.removeItem('token')
    localStorage.removeItem('userInfo')
    sessionStorage.removeItem('tonjclaw_demo_trial_dialog_shown')
    sessionStorage.removeItem('tonjclaw_demo_license')
  }
  
  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }
  
  return {
    userInfo,
    token,
    isLoggedIn,
    isAdmin,
    sidebarCollapsed,
    setToken,
    setUserInfo,
    logout,
    toggleSidebar
  }
})

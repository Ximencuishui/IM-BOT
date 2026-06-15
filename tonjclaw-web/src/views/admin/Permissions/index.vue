<template>
  <div class="permissions-page">
    <div class="page-header">
      <h2 class="page-title">权限管理</h2>
    </div>

    <el-tabs v-model="activeTab" type="border-card">
      <!-- 用户权限 -->
      <el-tab-pane label="用户权限" name="user-permissions">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>用户权限配置</span>
              <el-select v-model="selectedUser" placeholder="选择用户" style="width: 200px">
                <el-option 
                  v-for="user in users" 
                  :key="user.id" 
                  :label="user.username || user.email" 
                  :value="user.id"
                />
              </el-select>
            </div>
          </template>

          <div v-if="currentUserPermissions" class="permission-content">
            <el-descriptions :column="2" border style="margin-bottom: 20px;">
              <el-descriptions-item label="用户">
                {{ currentUserPermissions.username || currentUserPermissions.email }}
              </el-descriptions-item>
              <el-descriptions-item label="角色">
                <el-tag :type="getRoleTagType(currentUserPermissions.role)">
                  {{ getRoleText(currentUserPermissions.role) }}
                </el-tag>
              </el-descriptions-item>
            </el-descriptions>

            <div class="permission-groups">
              <div 
                v-for="group in permissionGroups" 
                :key="group.name" 
                class="permission-group"
              >
                <div class="group-header">
                  <el-icon><CollectionTag /></el-icon>
                  <span>{{ group.name }}</span>
                </div>
                <el-checkbox-group 
                  v-model="selectedPermissions" 
                  class="permission-checkboxes"
                >
                  <el-checkbox 
                    v-for="perm in getGroupPermissions(group.permissions)" 
                    :key="perm.code" 
                    :label="perm.code"
                  >
                    {{ perm.name }}
                  </el-checkbox>
                </el-checkbox-group>
              </div>
            </div>

            <div class="action-buttons">
              <el-button type="primary" @click="saveUserPermissions" :loading="saving">
                <el-icon><Operation /></el-icon> 保存权限
              </el-button>
            </div>
          </div>

          <el-empty v-else description="请选择用户查看权限" />
        </el-card>
      </el-tab-pane>

      <!-- 角色管理 -->
      <el-tab-pane label="角色管理" name="roles">
        <el-card>
          <template #header>
            <span>角色定义</span>
          </template>

          <el-table :data="roleList" border stripe>
            <el-table-column prop="code" label="角色编码" width="150" />
            <el-table-column prop="name" label="角色名称" width="120" />
            <el-table-column prop="description" label="角色描述" />
            <el-table-column prop="permissionCount" label="权限数量" width="100" />
            <el-table-column prop="permissions" label="权限列表">
              <template #default="{ row }">
                <div class="permission-tags">
                  <el-tag 
                    v-for="perm in row.permissions" 
                    :key="perm.code" 
                    size="small"
                    type="info"
                  >
                    {{ perm.name }}
                  </el-tag>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- 权限列表 -->
      <el-tab-pane label="权限列表" name="permission-list">
        <el-card>
          <template #header>
            <span>所有权限</span>
          </template>

          <el-table :data="permissionList" border stripe>
            <el-table-column prop="code" label="权限编码" width="200" />
            <el-table-column prop="name" label="权限名称" width="150" />
            <el-table-column prop="group" label="所属分组" width="120" />
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { CollectionTag, Operation } from '@element-plus/icons-vue'
import { 
  getAllPermissions, 
  getUserPermissions, 
  updateUserPermissions,
  getAllRoles,
  getRolePermissions
} from '../../../api/admin/permissions'
import { getUsers } from '../../../api/admin/users'

const activeTab = ref('user-permissions')
const selectedUser = ref(null)
const saving = ref(false)

const users = ref([])
const currentUserPermissions = ref(null)
const selectedPermissions = ref([])
const permissionGroups = ref([])
const allPermissions = ref({})

const roles = ref({})
const roleList = computed(() => {
  return Object.entries(roles.value).map(([code, data]) => ({
    code,
    ...data,
    permissionCount: data.permissions?.length || 0
  }))
})

const permissionList = computed(() => {
  const list = []
  permissionGroups.value.forEach(group => {
    group.permissions.forEach(permCode => {
      list.push({
        code: permCode,
        name: allPermissions.value[permCode] || permCode,
        group: group.name
      })
    })
  })
  return list
})

const loadUsers = async () => {
  try {
    const res = await getUsers({ page: 1, page_size: 100 })
    users.value = res.users || []
  } catch (error) {
    console.error('加载用户列表失败:', error)
  }
}

const loadPermissions = async () => {
  try {
    const res = await getAllPermissions()
    if (res.success) {
      allPermissions.value = res.permissions || {}
      permissionGroups.value = res.groups || []
    }
  } catch (error) {
    console.error('加载权限列表失败:', error)
  }
}

const loadRoles = async () => {
  try {
    const res = await getAllRoles()
    if (res.success) {
      roles.value = res.roles || {}
      
      for (const roleName of Object.keys(roles.value)) {
        const permRes = await getRolePermissions(roleName)
        if (permRes.success) {
          roles.value[roleName].permissions = permRes.permissions
        }
      }
    }
  } catch (error) {
    console.error('加载角色列表失败:', error)
  }
}

const loadUserPermissions = async (userId) => {
  try {
    const res = await getUserPermissions(userId)
    if (res.success) {
      currentUserPermissions.value = res
      selectedPermissions.value = [...res.permissions]
    }
  } catch (error) {
    console.error('加载用户权限失败:', error)
    currentUserPermissions.value = null
  }
}

const saveUserPermissions = async () => {
  if (!selectedUser.value) {
    ElMessage.warning('请选择用户')
    return
  }

  saving.value = true
  try {
    const res = await updateUserPermissions(selectedUser.value, selectedPermissions.value)
    if (res.success) {
      ElMessage.success('权限更新成功')
      await loadUserPermissions(selectedUser.value)
    } else {
      ElMessage.error(res.message || '更新失败')
    }
  } catch (error) {
    ElMessage.error('更新失败：' + error.message)
  } finally {
    saving.value = false
  }
}

const getGroupPermissions = (permCodes) => {
  return permCodes.map(code => ({
    code,
    name: allPermissions.value[code] || code
  }))
}

const getRoleText = (role) => {
  const map = {
    super_admin: '超级管理员',
    admin: '管理员',
    user: '普通用户'
  }
  return map[role] || role
}

const getRoleTagType = (role) => {
  const map = {
    super_admin: 'danger',
    admin: 'warning',
    user: 'info'
  }
  return map[role] || 'info'
}

watch(selectedUser, (val) => {
  if (val) {
    loadUserPermissions(val)
  } else {
    currentUserPermissions.value = null
    selectedPermissions.value = []
  }
})

onMounted(() => {
  loadUsers()
  loadPermissions()
  loadRoles()
})
</script>

<style scoped lang="scss">
.permissions-page {
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
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .permission-content {
    padding: 10px 0;
  }
  
  .permission-groups {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 20px;
    margin-bottom: 20px;
  }
  
  .permission-group {
    background: #f5f7fa;
    border-radius: 8px;
    padding: 15px;
    
    .group-header {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: bold;
      color: #303133;
      margin-bottom: 12px;
      padding-bottom: 8px;
      border-bottom: 1px solid #e4e7ed;
    }
    
    .permission-checkboxes {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
  }
  
  .action-buttons {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }
  
  .permission-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
}
</style>
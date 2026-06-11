<template>
  <el-container class="admin-root">
    <el-aside :width="isCollapse ? '64px' : '220px'" class="admin-aside">
      <div class="logo-area" @click="$router.push('/')">
        <el-icon :size="28"><Camera /></el-icon>
        <span v-show="!isCollapse" class="logo-text">无感考勤系统</span>
      </div>
      <el-menu :default-active="activeMenu" router :collapse="isCollapse" :collapse-transition="false"
        background-color="#304156" text-color="#bfcbd9" active-text-color="#409eff">
        <el-menu-item index="/admin/dashboard">
          <el-icon><DataAnalysis /></el-icon>
          <span>监控大屏</span>
        </el-menu-item>
        <el-menu-item index="/admin/members">
          <el-icon><User /></el-icon>
          <span>成员管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/camera">
          <el-icon><VideoCamera /></el-icon>
          <span>摄像头管理</span>
        </el-menu-item>
        <el-menu-item index="/admin/recognition-events">
          <el-icon><View /></el-icon>
          <span>识别事件</span>
        </el-menu-item>
        <el-menu-item index="/admin/attendance">
          <el-icon><Clock /></el-icon>
          <span>考勤记录</span>
        </el-menu-item>
        <el-menu-item index="/admin/logs">
          <el-icon><Document /></el-icon>
          <span>操作日志</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="admin-header">
        <div class="header-left">
          <el-icon class="collapse-btn" :size="22" @click="isCollapse = !isCollapse">
            <Fold v-if="!isCollapse" /><Expand v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/admin/dashboard' }">管理后台</el-breadcrumb-item>
            <el-breadcrumb-item>{{ breadcrumbTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-dropdown trigger="click" @command="handleCommand">
            <span class="user-dropdown">
              <el-avatar :size="32" icon="UserFilled" />
              <span class="username">{{ adminName }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout"><el-icon><SwitchButton /></el-icon> 退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="admin-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
const route = useRoute()
const router = useRouter()
const isCollapse = ref(false)
const adminName = computed(() => localStorage.getItem('admin_username') || '管理员')
const activeMenu = computed(() => route.path)
const breadcrumbTitle = computed(() => {
  const map = {
    '/admin/dashboard': '监控大屏', '/admin/members': '成员管理', '/admin/camera': '摄像头管理',
    '/admin/recognition-events': '识别事件', '/admin/attendance': '考勤记录', '/admin/logs': '操作日志'
  }
  return map[route.path] || ''
})
async function handleCommand(cmd) {
  if (cmd === 'logout') {
    try { await ElMessageBox.confirm('确定退出吗？', '提示', { type: 'info' }) } catch { return }
    localStorage.removeItem('admin_token'); localStorage.removeItem('admin_username')
    router.push('/admin/login')
  }
}
</script>

<style scoped>
.admin-root{height:100vh}.admin-aside{background:#304156;overflow:hidden;transition:width 0.3s}
.logo-area{height:60px;display:flex;align-items:center;justify-content:center;gap:10px;color:#fff;cursor:pointer;border-bottom:1px solid rgba(255,255,255,0.1)}
.logo-text{font-size:16px;font-weight:600;white-space:nowrap}.admin-aside .el-menu{border-right:none}
.admin-header{background:#fff;display:flex;align-items:center;justify-content:space-between;padding:0 20px;box-shadow:0 1px 4px rgba(0,0,0,0.08);z-index:10}
.header-left{display:flex;align-items:center;gap:16px}.collapse-btn{cursor:pointer;color:#666}.collapse-btn:hover{color:#409eff}
.header-right{display:flex;align-items:center;gap:12px}.user-dropdown{display:flex;align-items:center;gap:8px;cursor:pointer;color:#333}
.username{font-size:14px}.admin-main{background:#f0f2f5;padding:20px;overflow-y:auto}
</style>

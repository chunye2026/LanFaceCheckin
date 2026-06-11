import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'dashboard',
    component: () => import('../views/DashboardView.vue')
  },
  {
    path: '/admin/login',
    name: 'admin-login',
    component: () => import('../views/LoginView.vue')
  },
  {
    path: '/admin',
    component: () => import('../views/LayoutView.vue'),
    children: [
      { path: '', redirect: '/admin/dashboard' },
      { path: 'dashboard', name: 'admin-dashboard', component: () => import('../views/DashboardView.vue') },
      { path: 'members', name: 'admin-members', component: () => import('../views/admin/MemberView.vue') },
      { path: 'camera', name: 'admin-camera', component: () => import('../views/CameraView.vue') },
      { path: 'recognition-events', name: 'admin-events', component: () => import('../views/RecognitionEventView.vue') },
      { path: 'attendance', name: 'admin-attendance', component: () => import('../views/AttendanceView.vue') },
      { path: 'logs', name: 'admin-logs', component: () => import('../views/admin/LogView.vue') },
    ]
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  if (to.path.startsWith('/admin') && to.path !== '/admin/login') {
    const token = localStorage.getItem('admin_token')
    if (!token) {
      next('/admin/login')
      return
    }
  }
  next()
})

export default router

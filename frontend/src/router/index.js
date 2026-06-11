import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'checkin',
    component: () => import('../views/CheckinView.vue')
  },
  {
    path: '/admin/login',
    name: 'admin-login',
    component: () => import('../views/admin/LoginView.vue')
  },
  {
    path: '/admin',
    component: () => import('../views/admin/LayoutView.vue'),
    children: [
      {
        path: '',
        redirect: '/admin/members'
      },
      {
        path: 'members',
        name: 'admin-members',
        component: () => import('../views/admin/MemberView.vue')
      },
      {
        path: 'logs',
        name: 'admin-logs',
        component: () => import('../views/admin/LogView.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// 路由守卫：管理后台需要登录
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

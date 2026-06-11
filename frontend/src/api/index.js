import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 请求拦截器：自动附加token
api.interceptors.request.use(config => {
  const token = localStorage.getItem('admin_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：统一错误处理
api.interceptors.response.use(
  response => {
    const res = response.data
    if (res.code !== 200 && res.code !== undefined) {
      ElMessage.error(res.message || '请求失败')
      return Promise.reject(new Error(res.message))
    }
    return res
  },
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('admin_token')
      ElMessage.error('登录已过期，请重新登录')
      window.location.hash = '#/admin/login'
    } else {
      ElMessage.error(error.response?.data?.message || '网络错误')
    }
    return Promise.reject(error)
  }
)

/* ========== 认证 ========== */

export function login(username, password) {
  return api.post('/auth/login', { username, password })
}

export function getAdminInfo() {
  return api.get('/auth/info')
}

/* ========== 成员管理 ========== */

export function getMembers(params = {}) {
  return api.get('/members', { params })
}

export function getMember(id) {
  return api.get(`/members/${id}`)
}

export function createMember(data) {
  return api.post('/members', data)
}

export function updateMember(id, data) {
  return api.put(`/members/${id}`, data)
}

export function deleteMember(id) {
  return api.delete(`/members/${id}`)
}

export function uploadFace(memberId, file) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post(`/members/${memberId}/face`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function deleteFace(memberId) {
  return api.delete(`/members/${memberId}/face`)
}

/* ========== 打卡 ========== */

export function verifyFace(file) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/checkin/verify', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function doCheckin(data) {
  return api.post('/checkin/do', data)
}

export function getCheckRecords(params = {}) {
  return api.get('/checkin/records', { params })
}

export function getTodayStatus(memberId) {
  return api.get(`/checkin/today-status/${memberId}`)
}

/* ========== 日志 ========== */

export function getAuditLogs(params = {}) {
  return api.get('/logs', { params })
}

export function getActionTypes() {
  return api.get('/logs/action-types')
}

export default api

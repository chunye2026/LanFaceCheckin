import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('admin_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

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
  return api.post('/admin/login', { username, password })
}

export function changePassword(oldPassword, newPassword) {
  return api.post('/admin/change-password', { old_password: oldPassword, new_password: newPassword })
}

export function getAdminInfo() {
  return api.get('/admin/info')
}

/* ========== 成员管理 ========== */

export function getMembers(params = {}) {
  return api.get('/admin/members', { params })
}

export function createMember(data) {
  return api.post('/admin/members', data)
}

export function updateMember(id, data) {
  return api.put(`/admin/members/${id}`, data)
}

export function deleteMember(id) {
  return api.delete(`/admin/members/${id}`)
}

/* ========== 人脸样本 ========== */

export function getFaceSamples(memberId) {
  return api.get(`/admin/members/${memberId}/face-samples`)
}

export function uploadFaceSample(memberId, file) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post(`/admin/members/${memberId}/face-samples`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export function deleteFaceSample(sampleId) {
  return api.delete(`/admin/face-samples/${sampleId}`)
}

/* ========== 摄像头 ========== */

export function cameraStart() {
  return api.post('/admin/camera/start')
}

export function cameraStop() {
  return api.post('/admin/camera/stop')
}

export function cameraStatus() {
  return api.get('/admin/camera/status')
}

export function cameraSnapshot() {
  return api.get('/admin/camera/snapshot', { responseType: 'blob' })
}

/* ========== 识别事件 ========== */

export function getRecognitionEvents(params = {}) {
  return api.get('/admin/recognition-events', { params })
}

/* ========== 考勤记录 ========== */

export function getCheckinRecords(params = {}) {
  return api.get('/admin/checkin-records', { params })
}

export function manualCheckin(memberId, checkType) {
  return api.post('/admin/checkin-records/manual', { member_id: memberId, check_type: checkType })
}

/* ========== 系统 ========== */

export function getSystemStatus() {
  return api.get('/admin/system/status')
}

export function getOperationLogs(params = {}) {
  return api.get('/admin/operation-logs', { params })
}

/* ========== 打卡记录（公开） ========== */

export function getDashboardStatus() {
  return api.get('/dashboard/status')
}

export function getPublicRecords(params = {}) {
  return api.get('/checkin/records', { params })
}

export default api

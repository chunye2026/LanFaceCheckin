<template>
  <div class="checkin-root">
    <!-- 顶部 -->
    <el-header class="top-bar">
      <div class="top-left">
        <el-icon :size="28"><Camera /></el-icon>
        <span class="app-title">人脸识别打卡系统</span>
      </div>
      <div class="top-right">
        <el-tag effect="dark" type="warning" size="large" class="clock-tag">
          {{ currentTime }}
        </el-tag>
        <el-button text type="info" @click="$router.push('/admin/login')">
          管理后台
        </el-button>
      </div>
    </el-header>

    <!-- 主体 -->
    <div class="checkin-body">
      <el-row :gutter="20" class="main-row">
        <!-- 左侧：摄像头 -->
        <el-col :span="14">
          <el-card shadow="always" class="camera-card">
            <div class="camera-box">
              <video ref="videoRef" autoplay playsinline muted class="camera-video"></video>
              <canvas ref="canvasRef" class="camera-canvas"></canvas>

              <!-- 未开启摄像头 -->
              <div v-if="!cameraReady && !loading" class="camera-overlay">
                <el-icon :size="64" color="#dcdfe6"><VideoCamera /></el-icon>
                <p class="overlay-text">点击下方按钮开启摄像头</p>
              </div>

              <!-- 加载中 -->
              <div v-if="loading" class="camera-overlay">
                <el-icon :size="48" color="#409eff" class="loading-icon"><Loading /></el-icon>
                <p class="overlay-text">正在启动摄像头...</p>
              </div>
            </div>

            <div class="camera-actions">
              <el-button type="primary" size="large" :loading="loading" @click="startCamera"
                :disabled="cameraReady" round>
                <el-icon><VideoCamera /></el-icon> 开启摄像头
              </el-button>
              <el-button type="success" size="large" :loading="submitting" @click="checkIn('in')"
                :disabled="!cameraReady" round>
                <el-icon><CircleCheck /></el-icon> 签 到
              </el-button>
              <el-button type="warning" size="large" :loading="submitting" @click="checkIn('out')"
                :disabled="!cameraReady" round>
                <el-icon><CircleClose /></el-icon> 签 退
              </el-button>
            </div>

            <!-- 识别结果 -->
            <el-result v-if="resultShow" :icon="resultType" :title="resultTitle"
              :sub-title="resultMsg" class="check-result">
              <template v-if="resultType === 'success'" #extra>
                <el-descriptions :column="2" border size="small" style="margin-top:12px">
                  <el-descriptions-item label="姓名">{{ lastMember?.name }}</el-descriptions-item>
                  <el-descriptions-item label="工号">{{ lastMember?.employee_id }}</el-descriptions-item>
                  <el-descriptions-item label="部门">{{ lastMember?.department || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="置信度">{{ lastConfidence }}</el-descriptions-item>
                </el-descriptions>
              </template>
            </el-result>
          </el-card>
        </el-col>

        <!-- 右侧：今日记录 -->
        <el-col :span="10">
          <el-card shadow="always" class="record-card">
            <template #header>
              <div class="record-header">
                <span class="record-title">
                  <el-icon><Clock /></el-icon> 今日打卡记录
                </span>
                <el-button text type="primary" size="small" @click="refreshRecords">
                  <el-icon><Refresh /></el-icon>
                </el-button>
              </div>
            </template>

            <el-timeline v-if="todayRecords.length > 0">
              <el-timeline-item v-for="r in todayRecords" :key="r.id"
                :timestamp="formatTime(r.check_time)" placement="top"
                :type="r.check_type === 'in' ? 'success' : 'warning'"
                :icon="r.check_type === 'in' ? CircleCheck : CircleClose">
                <el-card shadow="hover" class="timeline-card" :body-style="{ padding: '10px 14px' }">
                  <span class="tl-name">{{ r.member_name }}</span>
                  <el-tag :type="r.check_type === 'in' ? 'success' : 'warning'" size="small" effect="dark">
                    {{ r.check_type === 'in' ? '签到' : '签退' }}
                  </el-tag>
                </el-card>
              </el-timeline-item>
            </el-timeline>

            <el-empty v-else description="暂无今日打卡记录" :image-size="80" />
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { verifyFace, doCheckin, getCheckRecords } from '../api/index.js'

const videoRef = ref(null)
const canvasRef = ref(null)
const cameraReady = ref(false)
const loading = ref(false)
const submitting = ref(false)
const currentTime = ref('')
const todayRecords = ref([])

// 结果展示
const resultShow = ref(false)
const resultType = ref('success')
const resultTitle = ref('')
const resultMsg = ref('')
const lastMember = ref(null)
const lastConfidence = ref(0)

let stream = null
let timerInterval = null

function updateTime() {
  const now = new Date()
  currentTime.value = now.toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    weekday: 'long'
  })
}

async function startCamera() {
  loading.value = true
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480, facingMode: 'user' }
    })
    videoRef.value.srcObject = stream
    cameraReady.value = true
    ElMessage.success('摄像头已就绪，请对准人脸进行打卡')
  } catch (err) {
    const msg = err.message || ''
    if (msg.includes('not allowed') || msg.includes('Permission')) {
      ElMessage.error('摄像头权限被拒绝，请在浏览器设置中允许摄像头访问')
    } else if (msg.includes('NotReadable') || msg.includes('NotFound')) {
      ElMessage.error('未检测到摄像头设备，请检查摄像头连接')
    } else {
      ElMessage({
        type: 'error',
        duration: 8000,
        dangerouslyUseHTMLString: true,
        message: `
          <div>
            <p style="margin-bottom:8px"><strong>摄像头访问失败</strong></p>
            <p style="font-size:13px;color:#999;margin-bottom:4px">可能原因：</p>
            <p style="font-size:13px;color:#999;margin:0">1. 非 HTTPS 或非 localhost 访问</p>
            <p style="font-size:13px;color:#999;margin:0">2. 请用 <b>https://127.0.0.1:5000</b> 访问</p>
            <p style="font-size:13px;color:#999;margin:0">详细: ${msg}</p>
          </div>
        `
      })
    }
  } finally {
    loading.value = false
  }
}

function stopCamera() {
  if (stream) {
    stream.getTracks().forEach(track => track.stop())
    stream = null
  }
  cameraReady.value = false
}

function capturePhoto() {
  const video = videoRef.value
  const canvas = canvasRef.value
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  canvas.getContext('2d').drawImage(video, 0, 0)
  return new Promise(resolve => {
    canvas.toBlob(blob => {
      resolve(new File([blob], 'checkin.jpg', { type: 'image/jpeg' }))
    }, 'image/jpeg', 0.9)
  })
}

async function checkIn(type) {
  submitting.value = true
  resultShow.value = false
  try {
    const file = await capturePhoto()
    const verifyRes = await verifyFace(file)
    const { member, confidence } = verifyRes.data

    await doCheckin({ member_id: member.id, check_type: type, confidence })

    lastMember.value = member
    lastConfidence.value = confidence

    const typeName = type === 'in' ? '签到' : '签退'
    resultType.value = 'success'
    resultTitle.value = `${typeName}成功`
    resultMsg.value = `${member.name}(${member.employee_id})`
    resultShow.value = true
    ElMessage.success(`${typeName}成功！`)

    refreshRecords()
    setTimeout(() => { resultShow.value = false }, 6000)
  } catch (err) {
    resultType.value = 'error'
    resultTitle.value = '识别失败'
    resultMsg.value = err.response?.data?.message || err.message || '打卡失败'
    resultShow.value = true
    setTimeout(() => { resultShow.value = false }, 5000)
  } finally {
    submitting.value = false
  }
}

function formatTime(isoStr) {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  const pad = n => String(n).padStart(2, '0')
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

async function refreshRecords() {
  try {
    const res = await getCheckRecords()
    const today = new Date().toISOString().slice(0, 10)
    todayRecords.value = (res.data.list || []).filter(r =>
      r.check_time?.startsWith(today)
    ).reverse()
  } catch { /* ignore */ }
}

timerInterval = setInterval(updateTime, 1000)
updateTime()

onMounted(refreshRecords)
onUnmounted(() => {
  stopCamera()
  clearInterval(timerInterval)
})
</script>

<style scoped>
.checkin-root {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e7ed 100%);
}

.top-bar {
  background: linear-gradient(135deg, #409eff 0%, #337ecc 100%);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 56px;
  color: #fff;
}

.top-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.app-title {
  font-size: 20px;
  font-weight: 600;
  letter-spacing: 1px;
}

.top-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.clock-tag {
  font-family: 'SF Mono', 'Monaco', monospace;
  font-size: 14px;
}

.checkin-body {
  padding: 20px;
  max-width: 1100px;
  margin: 0 auto;
}

.main-row {
  align-items: flex-start;
}

.camera-card {
  overflow: hidden;
}

.camera-card :deep(.el-card__body) {
  padding: 0;
}

.camera-box {
  position: relative;
  background: #000;
  aspect-ratio: 4/3;
}

.camera-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.camera-canvas {
  display: none;
}

.camera-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(0,0,0,0.6);
  gap: 16px;
}

.overlay-text {
  color: #ccc;
  font-size: 16px;
}

.loading-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.camera-actions {
  display: flex;
  gap: 12px;
  padding: 16px;
  justify-content: center;
  background: #fff;
  border-top: 1px solid #ebeef5;
}

.check-result {
  padding: 16px;
}

.record-card {
  max-height: calc(100vh - 116px);
  overflow-y: auto;
}

.record-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.record-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 16px;
  font-weight: 600;
}

.timeline-card {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.tl-name {
  font-weight: 500;
}

@media (max-width: 768px) {
  .main-row {
    flex-direction: column;
  }
}
</style>

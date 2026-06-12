<template>
  <el-card shadow="never">
    <template #header>
      <span><el-icon><VideoCamera /></el-icon> 摄像头管理</span>
    </template>

    <el-row :gutter="16">
      <!-- 实时画面 -->
      <el-col :span="14">
        <div class="stream-box">
          <img v-if="status.running" :src="streamUrl" class="stream-img" alt="Camera Stream" />
          <div v-else class="stream-placeholder">
            <el-icon :size="64" color="#c0c4cc"><VideoCamera /></el-icon>
            <p>摄像头未启动</p>
          </div>
        </div>
      </el-col>

      <!-- 状态和控制 -->
      <el-col :span="10">
        <el-descriptions :column="1" border size="small">
          <el-descriptions-item label="状态">
            <el-tag :type="status.running ? 'success' : 'info'">{{ status.running ? '运行中' : '已停止' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="帧率">{{ status.fps || 0 }} FPS</el-descriptions-item>
          <el-descriptions-item label="检测人脸">{{ status.detected_faces || 0 }}</el-descriptions-item>
          <el-descriptions-item label="模型">
            <el-tag :type="status.model_available ? 'success' : 'danger'" size="small">
              {{ status.model_available ? '可用' : '不可用' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="最后帧">{{ status.last_frame_time || '-' }}</el-descriptions-item>
          <el-descriptions-item label="错误">{{ status.last_error || '无' }}</el-descriptions-item>
        </el-descriptions>

        <div class="ctrl-btns">
          <el-button type="primary" :loading="starting" @click="startCamera" :disabled="status.running">
            <el-icon><VideoPlay /></el-icon> 启动识别
          </el-button>
          <el-button type="danger" :loading="stopping" @click="stopCamera" :disabled="!status.running">
            <el-icon><VideoPause /></el-icon> 停止识别
          </el-button>
        </div>
      </el-col>
    </el-row>
  </el-card>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { cameraStart, cameraStop, cameraStatus } from '../api/index.js'

const status = ref({ running: false, fps: 0, detected_faces: 0, model_available: false, last_frame_time: '', last_error: '' })
const starting = ref(false)
const stopping = ref(false)
const streamUrl = computed(() => {
  const token = localStorage.getItem('admin_token') || ''
  return `/api/admin/camera/stream?token=${encodeURIComponent(token)}`
})
let timer = null

async function refresh() {
  try { const r = await cameraStatus(); status.value = r.data || status.value } catch {}
}
async function startCamera() {
  starting.value = true
  try { await cameraStart(); ElMessage.success('摄像头已启动，正在识别...'); refresh() }
  catch {} finally { starting.value = false }
}
async function stopCamera() {
  stopping.value = true
  try { await cameraStop(); ElMessage.success('摄像头已停止'); refresh() }
  catch {} finally { stopping.value = false }
}

onMounted(() => { refresh(); timer = setInterval(refresh, 5000) })
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.stream-box {
  background: #000;
  border-radius: 8px;
  aspect-ratio: 4/3;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.stream-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.stream-placeholder {
  text-align: center;
  color: #909399;
}
.stream-placeholder p {
  margin-top: 12px;
  font-size: 15px;
}
.ctrl-btns {
  margin-top: 16px;
  display: flex;
  gap: 12px;
}
</style>

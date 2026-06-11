<template>
  <el-card shadow="never">
    <template #header>
      <span><el-icon><VideoCamera /></el-icon> 摄像头管理</span>
    </template>
    <el-descriptions :column="3" border>
      <el-descriptions-item label="状态">
        <el-tag :type="status.running ? 'success' : 'info'">{{ status.running ? '运行中' : '已停止' }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="FPS">{{ status.fps || 0 }}</el-descriptions-item>
      <el-descriptions-item label="检测人脸数">{{ status.detected_faces || 0 }}</el-descriptions-item>
      <el-descriptions-item label="模型状态">
        <el-tag :type="status.model_available ? 'success' : 'danger'">{{ status.model_available ? '可用' : '不可用' }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="最后帧时间">{{ status.last_frame_time || '-' }}</el-descriptions-item>
      <el-descriptions-item label="错误信息">{{ status.last_error || '无' }}</el-descriptions-item>
    </el-descriptions>
    <div style="margin-top:16px;display:flex;gap:12px">
      <el-button type="primary" :loading="starting" @click="startCamera" :disabled="status.running">
        <el-icon><VideoPlay /></el-icon> 启动识别
      </el-button>
      <el-button type="danger" :loading="stopping" @click="stopCamera" :disabled="!status.running">
        <el-icon><VideoPause /></el-icon> 停止识别
      </el-button>
      <el-button @click="refreshSnapshot" :disabled="!status.running">刷新快照</el-button>
    </div>
    <div v-if="snapshotUrl" style="margin-top:16px">
      <el-image :src="snapshotUrl" fit="contain" style="max-width:640px;border-radius:8px" />
    </div>
  </el-card>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { cameraStart, cameraStop, cameraStatus, cameraSnapshot } from '../api/index.js'

const status = ref({ running: false, fps: 0, detected_faces: 0, model_available: false, last_frame_time: '', last_error: '' })
const starting = ref(false), stopping = ref(false)
const snapshotUrl = ref('')
let timer = null

async function refresh() {
  try { const r = await cameraStatus(); status.value = r.data || status.value } catch {}
}
async function startCamera() {
  starting.value = true
  try { await cameraStart(); ElMessage.success('摄像头已启动'); refresh() } catch {}
  finally { starting.value = false }
}
async function stopCamera() {
  stopping.value = true
  try { await cameraStop(); ElMessage.success('摄像头已停止'); refresh() } catch {}
  finally { stopping.value = false }
}
async function refreshSnapshot() {
  try {
    const r = await cameraSnapshot()
    snapshotUrl.value = URL.createObjectURL(new Blob([r.data], { type: 'image/jpeg' }))
  } catch { ElMessage.error('获取快照失败') }
}
onMounted(() => { refresh(); timer = setInterval(refresh, 5000) })
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

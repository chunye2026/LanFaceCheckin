<template>
  <div class="dashboard">
    <!-- 顶部栏 -->
    <div class="dash-topbar">
      <span class="dash-title"><el-icon :size="22"><Camera /></el-icon> 无感考勤监控台</span>
      <div class="dash-top-right">
        <span class="dash-time">{{ currentTime }}</span>
        <el-button size="small" @click="$router.push('/admin/login')">后台管理</el-button>
      </div>
    </div>

    <!-- 顶部统计 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card" body-style="padding:18px">
          <div class="stat-num">{{ systemStatus.member_count || 0 }}</div>
          <div class="stat-label">成员总数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card" body-style="padding:18px">
          <div class="stat-num green">{{ systemStatus.today_checkin || 0 }} <small>人</small></div>
          <div class="stat-label">今日签到</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card" body-style="padding:18px">
          <div class="stat-num orange">{{ systemStatus.today_checkout || 0 }} <small>人</small></div>
          <div class="stat-label">今日签退</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card" body-style="padding:18px">
          <div class="stat-num" :class="systemStatus.model_available ? 'green' : 'red'">
            {{ systemStatus.model_available ? '就绪' : '异常' }}
          </div>
          <div class="stat-label">人脸模型</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 摄像头状态 -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-header">
          <span><el-icon><VideoCamera /></el-icon> 摄像头状态</span>
          <el-tag :type="cameraStatus.running ? 'success' : 'info'" effect="dark" size="small">
            {{ cameraStatus.running ? '运行中' : '已停止' }}
          </el-tag>
        </div>
      </template>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="帧率">{{ cameraStatus.fps || 0 }} FPS</el-descriptions-item>
            <el-descriptions-item label="检测人脸">{{ cameraStatus.detected_faces || 0 }}</el-descriptions-item>
            <el-descriptions-item label="模型">
              <el-tag :type="cameraStatus.model_available ? 'success' : 'danger'" size="small">{{ cameraStatus.model_available ? '可用' : '不可用' }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="最后帧">{{ cameraStatus.last_frame_time ? formatTime(cameraStatus.last_frame_time) : '-' }}</el-descriptions-item>
          </el-descriptions>
          <div v-if="cameraStatus.last_error" style="margin-top:12px">
            <el-alert :title="cameraStatus.last_error" type="error" :closable="false" show-icon />
          </div>
        </el-col>
        <el-col :span="12">
          <div class="mini-stream">
            <img v-if="cameraStatus.running" :src="streamUrl" class="mini-stream-img" alt="Live" />
            <div v-else class="mini-stream-placeholder">
              <el-icon :size="40" color="#c0c4cc"><VideoCamera /></el-icon>
              <span>摄像头未启动</span>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card shadow="never" class="section-card">
          <template #header>
            <div class="card-header">
              <span><el-icon><View /></el-icon> 最近识别事件</span>
            </div>
          </template>
          <el-empty v-if="recentEvents.length === 0" description="暂无识别事件" :image-size="60" />
          <el-table v-else :data="recentEvents" size="small" max-height="300">
            <el-table-column prop="member_name" label="成员" width="100">
              <template #default="{row}"><span v-if="row.member_name">{{row.member_name}}</span><el-tag v-else type="info" size="small">未识别</el-tag></template>
            </el-table-column>
            <el-table-column label="置信度" width="100">
              <template #default="{row}">{{(row.confidence*100).toFixed(1)}}%</template>
            </el-table-column>
            <el-table-column label="打卡" width="70" align="center">
              <template #default="{row}">
                <el-tag :type="row.checkin_created?'success':'warning'" size="small">{{row.checkin_created?'是':'否'}}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="时间" width="160">
              <template #default="{row}">{{formatTime(row.created_at)}}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="section-card">
          <template #header>
            <div class="card-header">
              <span><el-icon><Clock /></el-icon> 最近打卡记录</span>
            </div>
          </template>
          <el-empty v-if="recentRecords.length === 0" description="暂无打卡记录" :image-size="60" />
          <el-timeline v-else>
            <el-timeline-item v-for="r in recentRecords" :key="r.id"
              :timestamp="formatTime(r.check_time)" placement="top"
              :color="r.check_type==='in'?'#67c23a':'#e6a23c'">
              <span class="tl-name">{{r.member_name}}</span>
              <el-tag :type="r.check_type==='in'?'success':'warning'" size="small" effect="dark" style="margin-left:8px">
                {{r.check_type==='in'?'签到':'签退'}}
              </el-tag>
              <el-tag v-if="r.source==='manual_admin'" type="info" size="small" style="margin-left:8px">人工</el-tag>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { getDashboardStatus } from '../api/index.js'

const systemStatus = ref({})
const cameraStatus = ref({})
const recentEvents = ref([])
const recentRecords = ref([])
const currentTime = ref('')
const streamUrl = '/api/admin/camera/stream'
let timer = null

function updateClock() {
  const d = new Date()
  currentTime.value = d.toLocaleString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = n => String(n).padStart(2, '0')
  return `${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

async function refresh() {
  try {
    const res = await getDashboardStatus()
    if (res.data) {
      systemStatus.value = res.data.system || {}
      cameraStatus.value = res.data.camera || {}
      recentEvents.value = res.data.recent_events || []
      recentRecords.value = res.data.recent_records || []
    }
  } catch(e) { /* ignore */ }
}

onMounted(() => { updateClock(); refresh(); timer = setInterval(refresh, 3000); setInterval(updateClock, 1000) })
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<style scoped>
.dashboard {
  min-height: 100vh;
  background: #f0f2f5;
  padding: 0 0 16px 0;
  box-sizing: border-box;
}
.dash-topbar {
  background: linear-gradient(135deg, #409eff, #337ecc);
  color: #fff;
  padding: 0 24px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.dash-title { font-size: 18px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
.dash-top-right { display: flex; align-items: center; gap: 16px; }
.dash-time { font-family: monospace; font-size: 15px; opacity: 0.9; }
.stats-row { margin-bottom: 16px; max-width: 1400px; margin-left: auto; margin-right: auto; padding: 0 16px; }
.stat-card { text-align: center; }
.stat-num { font-size: 28px; font-weight: 700; color: #303133; }
.stat-num small { font-size: 14px; font-weight: 400; color: #909399; }
.stat-num.green { color: #67c23a; }
.stat-num.orange { color: #e6a23c; }
.stat-num.red { color: #f56c6c; }
.stat-label { font-size: 13px; color: #909399; margin-top: 4px; }
.section-card { margin-bottom: 16px; max-width: 1400px; margin-left: auto; margin-right: auto; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.tl-name { font-weight: 500; }
.mini-stream {
  background: #000;
  border-radius: 6px;
  height: 140px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.mini-stream-img { width: 100%; height: 100%; object-fit: contain; }
.mini-stream-placeholder { text-align: center; color: #909399; }
.mini-stream-placeholder span { display: block; margin-top: 8px; font-size: 13px; }
</style>

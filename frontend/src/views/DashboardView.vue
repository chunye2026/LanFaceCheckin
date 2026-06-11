<template>
  <div class="monitor">
    <!-- 顶栏 -->
    <header class="monitor-header">
      <div class="header-left">
        <el-icon :size="24"><Camera /></el-icon>
        <span class="header-title">无感考勤监控台</span>
        <span class="header-time">{{ currentTime }}</span>
      </div>
      <div class="header-right">
        <el-button text size="small" @click="$router.push('/admin/login')">
          <el-icon><User /></el-icon> 后台管理
        </el-button>
      </div>
    </header>

    <!-- 状态卡片行 -->
    <div class="stats-bar">
      <div class="stat-item" :class="statClass('camera')">
        <el-icon><VideoCamera /></el-icon>
        <span class="stat-label">摄像头</span>
        <span class="stat-val">{{ camera.running ? '运行' : '停止' }}</span>
      </div>
      <div class="stat-item" :class="statClass('model')">
        <el-icon><Cpu /></el-icon>
        <span class="stat-label">推理后端</span>
        <span class="stat-val">{{ stats.model_available ? 'ArcFace' : 'N/A' }}</span>
      </div>
      <div class="stat-item success">
        <el-icon><CircleCheck /></el-icon>
        <span class="stat-label">可选成员</span>
        <span class="stat-val">{{ stats.eligible_count }}/{{ stats.member_total }}</span>
      </div>
      <div class="stat-item success">
        <el-icon><Select /></el-icon>
        <span class="stat-label">今日签到</span>
        <span class="stat-val">{{ stats.today_checkin }}</span>
      </div>
      <div class="stat-item warning">
        <el-icon><CloseBold /></el-icon>
        <span class="stat-label">今日签退</span>
        <span class="stat-val">{{ stats.today_checkout }}</span>
      </div>
      <div class="stat-item" :class="alerts.length > 0 ? 'danger' : 'success'">
        <el-icon><Warning /></el-icon>
        <span class="stat-label">异常</span>
        <span class="stat-val">{{ alerts.length }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">阈值</span>
        <span class="stat-val">{{ (stats.threshold * 100).toFixed(0) }}%</span>
      </div>
    </div>

    <!-- 主体区域 -->
    <div class="monitor-body">
      <!-- 左侧: 摄像头画面 + 聚合事件 -->
      <div class="monitor-left">
        <!-- 主视觉区 -->
        <div class="camera-panel">
          <img v-if="camera.running" :src="streamUrl" class="camera-feed" />
          <div v-else class="camera-offline">
            <el-icon :size="64" color="#606266"><VideoCamera /></el-icon>
            <p>摄像头未启动</p>
          </div>
          <!-- 识别覆盖层 -->
          <div v-if="camera.running && lastRecog?.member_name" class="recog-overlay">
            <div class="recog-box">
              <div class="recog-name">{{ lastRecog.member_name }}</div>
              <div class="recog-conf">{{ (lastRecog.confidence*100).toFixed(1) }}%</div>
              <el-tag :type="lastRecog.matched ? 'success' : 'danger'" size="small" effect="dark">
                {{ lastRecog.matched ? '已识别' : '未匹配' }}
              </el-tag>
            </div>
          </div>
        </div>

        <!-- 异常提示 -->
        <div v-if="alerts.length > 0" class="alerts-area">
          <el-alert v-for="(a,i) in alerts" :key="i"
            :title="a.msg" :type="a.level === 'error' ? 'error' : 'warning'"
            :closable="false" show-icon class="alert-item" />
        </div>

        <!-- 聚合识别事件 -->
        <div class="events-panel">
          <h4><el-icon><View /></el-icon> 最近识别 (聚合)</h4>
          <div class="event-list">
            <div v-for="e in aggregatedEvents" :key="e.member_id || Math.random()" class="event-row"
              :class="e.checkin_created ? 'event-ok' : 'event-warn'">
              <span class="evt-name">{{ e.member_name || '陌生人' }}</span>
              <el-tag size="small" effect="dark" :type="e.matched ? 'success' : 'danger'">
                {{ (e.max_confidence*100 || e.confidence*100 || 0).toFixed(1) }}%
              </el-tag>
              <span v-if="e.count > 1" class="evt-count">×{{ e.count }}</span>
              <el-tag v-if="e.checkin_created" size="small" type="success" effect="dark">已打卡</el-tag>
              <span v-else-if="e.failure_reason" class="evt-reason">{{ reasonLabel(e.failure_reason) }}</span>
              <span class="evt-time">{{ formatTime(e.last_time || e.created_at) }}</span>
            </div>
            <el-empty v-if="aggregatedEvents.length === 0" description="暂无识别" :image-size="40" />
          </div>
        </div>
      </div>

      <!-- 右侧: 最近打卡 -->
      <div class="monitor-right">
        <div class="records-panel">
          <h4><el-icon><Clock /></el-icon> 最近有效打卡</h4>
          <div class="record-list">
            <div v-for="r in recentRecords" :key="r.id" class="record-row">
              <span class="rec-name">{{ r.member_name }}</span>
              <el-tag :type="r.check_type==='in'?'success':'warning'" size="small" effect="dark">
                {{ r.check_type==='in'?'签到':'签退' }}
              </el-tag>
              <el-tag v-if="r.source==='manual_admin'" type="info" size="small">人工</el-tag>
              <span class="rec-conf">{{ (r.confidence*100).toFixed(0) }}%</span>
              <span class="rec-time">{{ formatTime(r.check_time) }}</span>
            </div>
            <el-empty v-if="recentRecords.length === 0" description="无打卡" :image-size="40" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { getDashboardStatus } from '../api/index.js'

const stats = ref({})
const camera = ref({})
const alerts = ref([])
const aggregatedEvents = ref([])
const recentRecords = ref([])
const lastRecog = ref(null)
const currentTime = ref('')
const streamUrl = '/api/admin/camera/stream'
let timers = []

const reasonLabels = {
  cooldown_not_reached:'冷却中',already_checked_out:'已签退',confidence_too_low:'低置信',
  member_inactive:'已禁用',insufficient_face_samples:'样本不足',liveness_failed:'活体失败',
}

function reasonLabel(r) { return reasonLabels[r] || r }
function formatTime(iso) { if(!iso) return ''; const d=new Date(iso); const p=n=>String(n).padStart(2,'0'); return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}` }
function updateClock() { currentTime.value = new Date().toLocaleString('zh-CN', {hour:'2-digit',minute:'2-digit',second:'2-digit'}) }

function statClass(key) {
  if (key === 'camera') return camera.value.running ? 'success' : 'info'
  if (key === 'model') return stats.value.model_available ? 'success' : 'danger'
  return ''
}

async function refresh() {
  try {
    const res = await getDashboardStatus()
    const d = res.data || {}
    stats.value = d.stats || {}
    camera.value = d.camera || {}
    alerts.value = d.alerts || []
    aggregatedEvents.value = d.aggregated_events || []
    recentRecords.value = d.recent_records || []
    lastRecog.value = d.last_recognition || null
  } catch {}
}

onMounted(() => {
  updateClock(); refresh()
  timers.push(setInterval(refresh, 3000), setInterval(updateClock, 1000))
})
onUnmounted(() => timers.forEach(clearInterval))
</script>

<style scoped>
.monitor { display:flex; flex-direction:column; height:100vh; background:#1a1a2e; color:#e0e0e0; overflow:hidden; }

/* Header */
.monitor-header { display:flex; justify-content:space-between; align-items:center; padding:0 20px; height:48px; background:rgba(255,255,255,0.04); border-bottom:1px solid rgba(255,255,255,0.06); flex-shrink:0; }
.header-left { display:flex; align-items:center; gap:12px; }
.header-title { font-size:18px; font-weight:600; }
.header-time { font-family:monospace; font-size:14px; color:#909399; }
.header-right { display:flex; align-items:center; }

/* Stats bar */
.stats-bar { display:flex; gap:0; padding:0; border-bottom:1px solid rgba(255,255,255,0.06); flex-shrink:0; }
.stat-item { flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:10px 4px; border-right:1px solid rgba(255,255,255,0.04); gap:4px; transition:background 0.2s; }
.stat-item:last-child { border-right:none; }
.stat-item.success { color:#67c23a; }
.stat-item.warning { color:#e6a23c; }
.stat-item.danger { color:#f56c6c; background:rgba(245,108,108,0.08); }
.stat-item.info { color:#909399; }
.stat-item .stat-label { font-size:11px; text-transform:uppercase; letter-spacing:0.5px; }
.stat-item .stat-val { font-size:18px; font-weight:700; }
.stat-item .el-icon { font-size:18px; }

/* Body */
.monitor-body { display:flex; flex:1; overflow:hidden; }
.monitor-left { flex:1; display:flex; flex-direction:column; overflow-y:auto; padding:12px; gap:12px; min-width:0; }
.monitor-right { width:300px; flex-shrink:0; overflow-y:auto; padding:12px; border-left:1px solid rgba(255,255,255,0.06); }

/* Camera */
.camera-panel { position:relative; background:#000; border-radius:8px; overflow:hidden; aspect-ratio:16/10; max-height:50vh; }
.camera-feed { width:100%; height:100%; object-fit:contain; }
.camera-offline { display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; gap:12px; color:#909399; }
.recog-overlay { position:absolute; top:12px; left:12px; }
.recog-box { background:rgba(0,0,0,0.7); backdrop-filter:blur(4px); border-radius:8px; padding:8px 14px; display:flex; flex-direction:column; gap:4px; }
.recog-name { font-size:20px; font-weight:700; color:#fff; }
.recog-conf { font-size:14px; color:#67c23a; }

/* Alerts */
.alerts-area { display:flex; flex-direction:column; gap:4px; }
.alert-item { --el-alert-padding: 6px 12px; }

/* Events */
.events-panel { background:rgba(255,255,255,0.03); border-radius:8px; padding:12px; }
.events-panel h4, .records-panel h4 { margin:0 0 10px 0; font-size:14px; display:flex; align-items:center; gap:6px; }
.event-list { display:flex; flex-direction:column; gap:4px; }
.event-row { display:flex; align-items:center; gap:8px; padding:6px 8px; border-radius:6px; font-size:13px; }
.event-ok { background:rgba(103,194,58,0.08); }
.event-warn { background:rgba(230,162,60,0.06); }
.evt-name { font-weight:600; min-width:60px; }
.evt-count { color:#909399; font-size:11px; }
.evt-reason { color:#e6a23c; font-size:11px; }
.evt-time { margin-left:auto; color:#909399; font-size:11px; font-family:monospace; }

/* Records */
.records-panel { background:rgba(255,255,255,0.03); border-radius:8px; padding:12px; height:100%; }
.record-list { display:flex; flex-direction:column; gap:4px; }
.record-row { display:flex; align-items:center; gap:6px; padding:6px 8px; border-radius:6px; background:rgba(255,255,255,0.03); font-size:13px; }
.rec-name { font-weight:600; min-width:50px; }
.rec-conf { color:#909399; font-size:11px; }
.rec-time { margin-left:auto; color:#909399; font-size:11px; font-family:monospace; }
</style>

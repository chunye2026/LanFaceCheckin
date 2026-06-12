<template>
  <div class="monitor">
    <header class="monitor-header">
      <div class="brand">
        <div class="brand-icon"><el-icon><Camera /></el-icon></div>
        <div>
          <div class="header-title">无感考勤监控台</div>
          <div class="header-subtitle">{{ camera.running ? '实时识别中' : '摄像头未启动' }} · {{ currentDate }}</div>
        </div>
      </div>
      <div class="header-meta">
        <div class="clock">{{ currentTime }}</div>
        <el-button text size="small" @click="$router.push('/admin/login')"><el-icon><User /></el-icon> 后台管理</el-button>
      </div>
    </header>

    <section class="stats-grid">
      <div class="metric" :class="camera.running ? 'ok' : 'muted'">
        <el-icon><VideoCamera /></el-icon>
        <span>摄像头</span>
        <strong>{{ camera.running ? '运行' : '停止' }}</strong>
      </div>
      <div class="metric" :class="stats.model_available ? 'ok' : 'bad'">
        <el-icon><Cpu /></el-icon>
        <span>模型</span>
        <strong>{{ stats.model_available ? 'ArcFace' : 'N/A' }}</strong>
      </div>
      <div class="metric">
        <el-icon><View /></el-icon>
        <span>人脸</span>
        <strong>{{ camera.detected_faces || 0 }}</strong>
      </div>
      <div class="metric ok">
        <span>签到</span>
        <strong>{{ stats.today_checkin || 0 }}</strong>
      </div>
      <div class="metric warn">
        <span>签退</span>
        <strong>{{ stats.today_checkout || 0 }}</strong>
      </div>
      <div class="metric" :class="alerts.length ? 'bad' : 'ok'">
        <span>告警</span>
        <strong>{{ alerts.length }}</strong>
      </div>
      <div class="metric">
        <span>FPS</span>
        <strong>{{ camera.fps || 0 }}</strong>
      </div>
    </section>

    <main class="monitor-body">
      <section class="camera-zone">
        <div class="camera-panel">
          <img v-if="camera.running" :src="streamUrl" class="camera-feed" alt="Dashboard Stream" />
          <div v-else class="camera-offline">
            <el-icon :size="72"><VideoCamera /></el-icon>
            <p>摄像头未启动</p>
          </div>
          <div class="camera-overlay">
            <div class="live-pill" :class="{ active: camera.running }">
              <span></span>{{ camera.running ? 'LIVE' : 'OFFLINE' }}
            </div>
            <div v-if="camera.running" class="det-bar">
              <b>{{ detections.length }}</b> 人脸 · <b>{{ matchedCount }}</b> 已识别 · <b>{{ checkedInCount }}</b> 已打卡
            </div>
          </div>
        </div>

        <div v-if="alerts.length" class="alerts-area">
          <el-alert v-for="(a,i) in alerts" :key="i" :title="a.msg" :type="a.level==='error'?'error':'warning'" :closable="false" show-icon />
        </div>

        <div class="lower-grid">
          <section class="panel attendance-panel">
            <div class="panel-title"><el-icon><DataAnalysis /></el-icon> 综合考勤</div>
            <div class="summary-grid">
              <div class="summary-card">
                <div class="summary-head">
                  <span>本周</span>
                  <strong :class="rateClass(summary.week?.attendance_rate)">{{ summary.week?.attendance_rate || 0 }}%</strong>
                </div>
                <div class="bar"><i :style="{ width: `${summary.week?.attendance_rate || 0}%` }"></i></div>
                <div class="summary-lines">
                  <span>工作日 {{ summary.week?.work_days || 0 }} 天</span>
                  <span>已出勤 {{ summary.week?.actual_person_days || 0 }} / {{ summary.week?.expected_person_days || 0 }}</span>
                  <span>未考勤 {{ summary.week?.absent_person_days || 0 }}</span>
                </div>
              </div>
              <div class="summary-card">
                <div class="summary-head">
                  <span>本月</span>
                  <strong :class="rateClass(summary.month?.attendance_rate)">{{ summary.month?.attendance_rate || 0 }}%</strong>
                </div>
                <div class="bar"><i :style="{ width: `${summary.month?.attendance_rate || 0}%` }"></i></div>
                <div class="summary-lines">
                  <span>工作日 {{ summary.month?.work_days || 0 }} 天</span>
                  <span>已出勤 {{ summary.month?.actual_person_days || 0 }} / {{ summary.month?.expected_person_days || 0 }}</span>
                  <span>未考勤 {{ summary.month?.absent_person_days || 0 }}</span>
                </div>
              </div>
            </div>
          </section>

          <section class="panel records-panel">
            <div class="panel-title"><el-icon><Clock /></el-icon> 最近有效打卡</div>
            <div class="record-list">
              <div v-for="r in recentRecords.slice(0, 6)" :key="r.id" class="record-row">
                <div class="avatar">{{ nameInitial(r.member_name) }}</div>
                <div class="rec-main">
                  <strong>{{ r.member_name }}</strong>
                  <span>{{ formatTime(r.check_time) }}</span>
                </div>
                <el-tag :type="r.check_type==='in'?'success':'warning'" size="small" effect="dark">{{ r.check_type==='in'?'签到':'签退' }}</el-tag>
              </div>
              <el-empty v-if="!recentRecords.length" description="暂无打卡" :image-size="40" />
            </div>
          </section>
        </div>
      </section>

      <aside class="side-zone">
        <section class="panel event-panel">
          <div class="panel-title"><el-icon><View /></el-icon> 识别事件</div>
          <div class="event-list">
            <div v-for="e in aggregatedEvents" :key="eventKey(e)" class="event-row" :class="eventClass(e)">
              <div class="event-top">
                <strong>{{ e.member_name || '陌生人' }}</strong>
                <span>{{ formatTime(e.last_time || e.created_at) }}</span>
              </div>
              <div class="event-bottom">
                <el-tag size="small" effect="dark" :type="e.matched ? 'success' : 'danger'">{{ confidenceText(e) }}</el-tag>
                <el-tag v-if="e.checkin_created" size="small" type="success" effect="dark">已打卡</el-tag>
                <span v-else-if="e.failure_reason" class="evt-reason">{{ reasonLabel(e.failure_reason) }}</span>
                <span v-if="e.count > 1" class="evt-count">x{{ e.count }}</span>
              </div>
            </div>
            <el-empty v-if="!aggregatedEvents.length" description="暂无识别" :image-size="46" />
          </div>
        </section>

        <section class="panel rank-panel">
          <div class="panel-title">缺勤排行</div>
          <div class="rank-tabs">
            <button :class="{ active: rankPeriod === 'week' }" @click="rankPeriod = 'week'">本周</button>
            <button :class="{ active: rankPeriod === 'month' }" @click="rankPeriod = 'month'">本月</button>
          </div>
          <div class="rank-list">
            <div v-for="(r,i) in activeRanking" :key="r.member_id" class="rank-row">
              <span class="rk-num">{{ i + 1 }}</span>
              <div class="rk-main">
                <strong>{{ r.name }}</strong>
                <span>{{ r.department || '未分组' }}</span>
              </div>
              <b>缺 {{ r.absent_days }} 天</b>
            </div>
            <el-empty v-if="!activeRanking.length" description="暂无数据" :image-size="40" />
          </div>
        </section>
      </aside>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { getDashboardStatus, getAttendanceSummary } from '../api/index.js'
import { formatTime, reasonLabel } from '../utils/index.js'

const stats = ref({})
const camera = ref({})
const alerts = ref([])
const aggregatedEvents = ref([])
const recentRecords = ref([])
const summary = ref({ week: {}, month: {} })
const currentTime = ref('')
const currentDate = ref('')
const streamUrl = '/api/dashboard/stream'
const detections = ref([])
const rankPeriod = ref('week')
let timers = []

const matchedCount = computed(() => detections.value.filter(d => d.matched).length)
const checkedInCount = computed(() => detections.value.filter(d => d.checkin_created).length)
const activeRanking = computed(() => summary.value[rankPeriod.value]?.ranking || [])

function updateClock() {
  const now = new Date()
  currentTime.value = now.toLocaleString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  currentDate.value = now.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', weekday: 'long' })
}

function rateClass(rate = 0) {
  if (rate >= 90) return 'green'
  if (rate >= 75) return 'amber'
  return 'red'
}

function nameInitial(name = '') {
  return String(name || '?').slice(0, 1)
}

function confidenceText(e) {
  const value = (e.max_confidence || e.confidence || 0) * 100
  return `${value.toFixed(1)}%`
}

function eventClass(e) {
  if (!e.matched) return 'event-bad'
  if (e.checkin_created) return 'event-ok'
  return 'event-warn'
}

function eventKey(e) {
  return `${e.member_id || 'unknown'}-${e.last_time || e.created_at || ''}-${e.failure_reason || ''}`
}

async function refresh() {
  try {
    const [statusRes, attRes] = await Promise.all([
      getDashboardStatus().catch(() => ({ data: {} })),
      getAttendanceSummary().catch(() => ({ data: { week: {}, month: {} } })),
    ])
    const d = statusRes.data || {}
    stats.value = d.stats || {}
    camera.value = d.camera || {}
    alerts.value = d.alerts || []
    aggregatedEvents.value = d.aggregated_events || []
    recentRecords.value = d.recent_records || []
    detections.value = d.camera?.current_detections || []
    summary.value = attRes.data || { week: {}, month: {} }
  } catch {}
}

onMounted(() => {
  updateClock()
  refresh()
  timers.push(setInterval(refresh, 3000), setInterval(updateClock, 1000))
})
onUnmounted(() => timers.forEach(clearInterval))
</script>

<style scoped>
.monitor { min-height: 100vh; height: 100vh; display: flex; flex-direction: column; overflow: hidden; color: #eef6f8; background: radial-gradient(circle at 18% 0%, rgba(25, 90, 108, 0.28), transparent 30%), linear-gradient(135deg, #101820 0%, #16202a 52%, #0e1419 100%); }
.monitor-header { height: 68px; flex-shrink: 0; display: flex; align-items: center; justify-content: space-between; padding: 0 24px; border-bottom: 1px solid rgba(255,255,255,0.08); background: rgba(8, 14, 18, 0.55); }
.brand { display: flex; align-items: center; gap: 14px; }
.brand-icon { width: 42px; height: 42px; display: grid; place-items: center; border-radius: 8px; background: #1f8a70; color: #ffffff; font-size: 22px; box-shadow: 0 0 24px rgba(31, 138, 112, 0.35); }
.header-title { font-size: 22px; font-weight: 800; letter-spacing: 0; }
.header-subtitle { margin-top: 4px; color: #9db4bd; font-size: 12px; }
.header-meta { display: flex; align-items: center; gap: 16px; }
.clock { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 28px; font-weight: 800; color: #f8d66d; }

.stats-grid { flex-shrink: 0; display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 10px; padding: 12px 16px; border-bottom: 1px solid rgba(255,255,255,0.06); }
.metric { min-width: 0; height: 76px; display: flex; flex-direction: column; justify-content: center; gap: 4px; padding: 0 14px; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; background: rgba(255,255,255,0.055); }
.metric .el-icon { font-size: 18px; color: #89c2d9; }
.metric span { color: #9db4bd; font-size: 12px; }
.metric strong { color: #ffffff; font-size: 24px; line-height: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.metric.ok strong, .green { color: #64d58a; }
.metric.warn strong, .amber { color: #f8d66d; }
.metric.bad strong, .red { color: #ff6b6b; }
.metric.muted strong { color: #97a4aa; }

.monitor-body { flex: 1; min-height: 0; display: grid; grid-template-columns: minmax(0, 1fr) 360px; gap: 14px; padding: 0 16px 16px; overflow: hidden; }
.camera-zone { min-width: 0; min-height: 0; display: flex; flex-direction: column; gap: 12px; overflow: hidden; }
.side-zone { min-height: 0; display: flex; flex-direction: column; gap: 12px; overflow: hidden; }

.camera-panel { position: relative; flex: 1; min-height: 280px; background: #030608; border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; overflow: hidden; box-shadow: 0 18px 48px rgba(0,0,0,0.24); }
.camera-feed { width: 100%; height: 100%; display: block; object-fit: contain; }
.camera-offline { height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px; color: #6f8088; }
.camera-offline p { margin: 0; font-size: 18px; }
.camera-overlay { position: absolute; inset: 14px 14px auto 14px; display: flex; justify-content: space-between; align-items: center; gap: 12px; pointer-events: none; }
.live-pill { display: inline-flex; align-items: center; gap: 8px; height: 30px; padding: 0 12px; border-radius: 6px; color: #c7d2d7; background: rgba(0,0,0,0.55); font-family: ui-monospace, SFMono-Regular, Consolas, monospace; font-size: 12px; font-weight: 800; }
.live-pill span { width: 8px; height: 8px; border-radius: 50%; background: #7f8b90; }
.live-pill.active span { background: #64d58a; box-shadow: 0 0 14px #64d58a; }
.det-bar { max-width: 70%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; background: rgba(0,0,0,0.58); color: #d7edf2; padding: 6px 12px; border-radius: 6px; font-size: 13px; }
.det-bar b { color: #f8d66d; }

.alerts-area { display: flex; flex-direction: column; gap: 4px; flex-shrink: 0; }
.lower-grid { flex-shrink: 0; display: grid; grid-template-columns: 1.35fr 1fr; gap: 12px; min-height: 210px; }
.panel { min-width: 0; border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; background: rgba(255,255,255,0.055); padding: 14px; overflow: hidden; }
.panel-title { height: 24px; display: flex; align-items: center; gap: 8px; margin-bottom: 12px; color: #e8f3f6; font-size: 15px; font-weight: 800; }

.summary-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.summary-card { border-radius: 8px; background: rgba(0,0,0,0.18); padding: 14px; }
.summary-head { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; }
.summary-head span { color: #9db4bd; font-size: 13px; }
.summary-head strong { font-size: 28px; line-height: 1; }
.bar { height: 8px; margin: 12px 0; border-radius: 999px; background: rgba(255,255,255,0.12); overflow: hidden; }
.bar i { display: block; height: 100%; max-width: 100%; border-radius: inherit; background: linear-gradient(90deg, #1f8a70, #f8d66d); }
.summary-lines { display: grid; gap: 5px; color: #b8c8ce; font-size: 12px; }

.record-list, .event-list, .rank-list { display: flex; flex-direction: column; gap: 8px; }
.record-row { display: flex; align-items: center; gap: 10px; min-height: 44px; padding: 7px 8px; border-radius: 7px; background: rgba(0,0,0,0.18); }
.avatar { width: 30px; height: 30px; flex: 0 0 30px; display: grid; place-items: center; border-radius: 7px; background: #2d6a8a; color: #ffffff; font-weight: 800; }
.rec-main { min-width: 0; flex: 1; display: grid; gap: 2px; }
.rec-main strong, .event-top strong, .rk-main strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rec-main span, .event-top span, .rk-main span { color: #9db4bd; font-size: 12px; }

.event-panel { flex: 1.1; min-height: 0; }
.event-list { max-height: calc(100% - 36px); overflow-y: auto; padding-right: 2px; }
.event-row { padding: 10px; border-radius: 8px; background: rgba(0,0,0,0.18); border-left: 4px solid #f8d66d; }
.event-row.event-ok { border-left-color: #64d58a; }
.event-row.event-bad { border-left-color: #ff6b6b; }
.event-top, .event-bottom { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.event-bottom { margin-top: 8px; justify-content: flex-start; flex-wrap: wrap; }
.evt-reason { color: #f8d66d; font-size: 12px; }
.evt-count { margin-left: auto; color: #9db4bd; font-size: 12px; }

.rank-panel { flex: 0.9; min-height: 0; }
.rank-tabs { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-bottom: 10px; }
.rank-tabs button { height: 30px; border: 1px solid rgba(255,255,255,0.1); border-radius: 6px; color: #b8c8ce; background: rgba(0,0,0,0.14); cursor: pointer; }
.rank-tabs button.active { color: #ffffff; background: #2d6a8a; border-color: #2d6a8a; }
.rank-list { max-height: calc(100% - 76px); overflow-y: auto; }
.rank-row { display: grid; grid-template-columns: 28px minmax(0, 1fr) auto; align-items: center; gap: 10px; padding: 8px; border-radius: 7px; background: rgba(0,0,0,0.16); }
.rk-num { width: 26px; height: 26px; display: grid; place-items: center; border-radius: 6px; background: rgba(255,255,255,0.1); color: #f8d66d; font-weight: 800; }
.rk-main { min-width: 0; display: grid; gap: 2px; }
.rank-row b { color: #ffb86b; font-size: 12px; white-space: nowrap; }

:deep(.el-button.is-text) { color: #d7edf2; }
:deep(.el-empty__description p) { color: #9db4bd; }

@media (max-width: 1100px) {
  .stats-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .monitor-body { grid-template-columns: 1fr; overflow-y: auto; }
  .side-zone { min-height: 520px; }
}

@media (max-width: 720px) {
  .monitor { height: auto; min-height: 100vh; overflow: auto; }
  .monitor-header { height: auto; padding: 12px; align-items: flex-start; gap: 12px; }
  .header-meta { align-items: flex-end; flex-direction: column; gap: 6px; }
  .clock { font-size: 22px; }
  .stats-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); padding: 10px; }
  .monitor-body { padding: 0 10px 10px; }
  .lower-grid, .summary-grid { grid-template-columns: 1fr; }
}
</style>

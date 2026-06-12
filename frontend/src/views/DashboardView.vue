<template>
  <div class="monitor">
    <header class="monitor-header">
      <div class="header-left">
        <el-icon :size="24"><Camera /></el-icon>
        <span class="header-title">无感考勤监控台</span>
        <span class="header-time">{{ currentTime }}</span>
      </div>
      <div class="header-right">
        <el-button text size="small" @click="$router.push('/admin/login')"><el-icon><User /></el-icon> 后台管理</el-button>
      </div>
    </header>

    <!-- 状态栏 -->
    <div class="stats-bar">
      <div class="stat-item" :class="camera.running?'success':'info'">
        <el-icon><VideoCamera /></el-icon><span class="stat-label">摄像头</span>
        <span class="stat-val">{{ camera.running ? '运行' : '停止' }}</span>
      </div>
      <div class="stat-item" :class="stats.model_available?'success':'danger'">
        <el-icon><Cpu /></el-icon><span class="stat-label">推理</span>
        <span class="stat-val">{{ stats.model_available ? 'ArcFace' : 'N/A' }}</span>
      </div>
      <div class="stat-item">
        <el-icon><View /></el-icon><span class="stat-label">检测人脸</span>
        <span class="stat-val">{{ camera.detected_faces || 0 }}</span>
      </div>
      <div class="stat-item success">
        <span class="stat-label">今日签到</span>
        <span class="stat-val">{{ stats.today_checkin }}</span>
      </div>
      <div class="stat-item warning">
        <span class="stat-label">今日签退</span>
        <span class="stat-val">{{ stats.today_checkout }}</span>
      </div>
      <div class="stat-item" :class="alerts.length?'danger':'success'">
        <span class="stat-label">异常</span>
        <span class="stat-val">{{ alerts.length }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">FPS</span>
        <span class="stat-val">{{ camera.fps || 0 }}</span>
      </div>
    </div>

    <div class="monitor-body">
      <div class="monitor-left">
        <!-- 摄像头画面(带框) -->
        <div class="camera-panel">
          <img v-if="camera.running" :src="streamUrl" class="camera-feed" />
          <div v-else class="camera-offline"><el-icon :size="64" color="#606266"><VideoCamera /></el-icon><p>摄像头未启动</p></div>
          <!-- 顶部识别状态条 -->
          <div v-if="camera.running && detections.length" class="det-bar">
            检测: {{ detections.length }}人脸 | {{ matchedCount }}已识别 | {{ checkedInCount }}已打卡 | FPS:{{ camera.fps }}
          </div>
        </div>

        <!-- 异常 -->
        <div v-if="alerts.length" class="alerts-area">
          <el-alert v-for="(a,i) in alerts" :key="i" :title="a.msg" :type="a.level==='error'?'error':'warning'" :closable="false" show-icon />
        </div>

        <!-- 最近打卡 -->
        <div class="events-panel">
          <h4><el-icon><Clock /></el-icon> 最近有效打卡</h4>
          <div class="record-list">
            <div v-for="r in recentRecords" :key="r.id" class="record-row">
              <span class="rec-name">{{ r.member_name }}</span>
              <el-tag :type="r.check_type==='in'?'success':'warning'" size="small" effect="dark">{{ r.check_type==='in'?'签到':'签退' }}</el-tag>
              <el-tag v-if="r.source==='manual_admin'" type="info" size="small">人工</el-tag>
              <span class="rec-time">{{ formatTime(r.check_time) }}</span>
            </div>
            <el-empty v-if="!recentRecords.length" description="暂无打卡" :image-size="40" />
          </div>
        </div>

        <!-- 综合考勤 -->
        <div class="attendance-panel">
          <h4><el-icon><DataAnalysis /></el-icon> 综合考勤统计</h4>
          <el-row :gutter="12" class="summary-cards">
            <el-col :span="12">
              <div class="sum-card">
                <div class="sum-title">本周</div>
                <div class="sum-row">工作日 <b>{{ summary.week?.work_days || 0 }}</b> 天</div>
                <div class="sum-row">应出勤 <b>{{ summary.week?.expected_person_days || 0 }}</b> 人次</div>
                <div class="sum-row">已出勤 <b class="green">{{ summary.week?.actual_person_days || 0 }}</b> 人次</div>
                <div class="sum-row">未考勤 <b class="red">{{ summary.week?.absent_person_days || 0 }}</b> 人次</div>
                <div class="sum-row">出勤率 <b :class="(summary.week?.attendance_rate||0)>=80?'green':'red'">{{ summary.week?.attendance_rate || 0 }}%</b></div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="sum-card">
                <div class="sum-title">本月</div>
                <div class="sum-row">工作日 <b>{{ summary.month?.work_days || 0 }}</b> 天</div>
                <div class="sum-row">应出勤 <b>{{ summary.month?.expected_person_days || 0 }}</b> 人次</div>
                <div class="sum-row">已出勤 <b class="green">{{ summary.month?.actual_person_days || 0 }}</b> 人次</div>
                <div class="sum-row">未考勤 <b class="red">{{ summary.month?.absent_person_days || 0 }}</b> 人次</div>
                <div class="sum-row">出勤率 <b :class="(summary.month?.attendance_rate||0)>=80?'green':'red'">{{ summary.month?.attendance_rate || 0 }}%</b></div>
              </div>
            </el-col>
          </el-row>

          <!-- 排名 -->
          <el-row :gutter="12" style="margin-top:12px">
            <el-col :span="12">
              <div class="rank-box">
                <div class="rank-title">本周缺勤排行</div>
                <div v-for="(r,i) in (summary.week?.ranking || [])" :key="r.member_id" class="rank-row" :class="i<3?'rank-top':''">
                  <span class="rk-num">#{{ i+1 }}</span>
                  <span class="rk-name">{{ r.name }}</span>
                  <span class="rk-dept">{{ r.department }}</span>
                  <span class="rk-abs">缺{{ r.absent_days }}天</span>
                </div>
                <el-empty v-if="!(summary.week?.ranking||[]).length" description="暂无数据" :image-size="30" />
              </div>
            </el-col>
            <el-col :span="12">
              <div class="rank-box">
                <div class="rank-title">本月缺勤排行</div>
                <div v-for="(r,i) in (summary.month?.ranking || [])" :key="r.member_id" class="rank-row" :class="i<3?'rank-top':''">
                  <span class="rk-num">#{{ i+1 }}</span>
                  <span class="rk-name">{{ r.name }}</span>
                  <span class="rk-dept">{{ r.department }}</span>
                  <span class="rk-abs">缺{{ r.absent_days }}天</span>
                </div>
                <el-empty v-if="!(summary.month?.ranking||[]).length" description="暂无数据" :image-size="30" />
              </div>
            </el-col>
          </el-row>
        </div>
      </div>

      <div class="monitor-right">
        <div class="records-panel">
          <h4><el-icon><View /></el-icon> 识别事件</h4>
          <div class="event-list">
            <div v-for="e in aggregatedEvents" :key="e.member_id||Math.random()" class="event-row" :class="e.checkin_created?'event-ok':'event-warn'">
              <span class="evt-name">{{ e.member_name||'陌生人' }}</span>
              <el-tag size="small" effect="dark" :type="e.matched?'success':'danger'">{{ (e.max_confidence*100||e.confidence*100||0).toFixed(1) }}%</el-tag>
              <span v-if="e.count>1" class="evt-count">×{{ e.count }}</span>
              <el-tag v-if="e.checkin_created" size="small" type="success" effect="dark">已打卡</el-tag>
              <span v-else-if="e.failure_reason" class="evt-reason">{{ reasonLabel(e.failure_reason) }}</span>
              <span class="evt-time">{{ formatTime(e.last_time||e.created_at) }}</span>
            </div>
            <el-empty v-if="!aggregatedEvents.length" description="暂无" :image-size="40" />
          </div>
        </div>
      </div>
    </div>
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
const streamUrl = '/api/dashboard/stream'
const detections = ref([])
let timers = []

const matchedCount = computed(() => detections.value.filter(d => d.matched).length)
const checkedInCount = computed(() => detections.value.filter(d => d.checkin_created).length)

function updateClock() { currentTime.value = new Date().toLocaleString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) }

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

onMounted(() => { updateClock(); refresh(); timers.push(setInterval(refresh, 3000), setInterval(updateClock, 1000)) })
onUnmounted(() => timers.forEach(clearInterval))
</script>

<style scoped>
.monitor { display: flex; flex-direction: column; height: 100vh; background: #1a1a2e; color: #e0e0e0; overflow: hidden; }
.monitor-header { display: flex; justify-content: space-between; align-items: center; padding: 0 20px; height: 48px; background: rgba(255,255,255,0.04); border-bottom: 1px solid rgba(255,255,255,0.06); flex-shrink: 0; }
.header-left { display: flex; align-items: center; gap: 12px; }
.header-title { font-size: 18px; font-weight: 600; }
.header-time { font-family: monospace; font-size: 14px; color: #909399; }
.header-right { display: flex; align-items: center; }

.stats-bar { display: flex; border-bottom: 1px solid rgba(255,255,255,0.06); flex-shrink: 0; }
.stat-item { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 8px 4px; border-right: 1px solid rgba(255,255,255,0.04); gap: 2px; }
.stat-item:last-child { border-right: none; }
.stat-item.success { color: #67c23a; }
.stat-item.warning { color: #e6a23c; }
.stat-item.danger { color: #f56c6c; background: rgba(245,108,108,0.08); }
.stat-item.info { color: #909399; }
.stat-item .stat-label { font-size: 10px; letter-spacing: 0.5px; }
.stat-item .stat-val { font-size: 16px; font-weight: 700; }
.stat-item .el-icon { font-size: 16px; }

.monitor-body { display: flex; flex: 1; overflow: hidden; }
.monitor-left { flex: 1; display: flex; flex-direction: column; overflow-y: auto; padding: 10px; gap: 10px; min-width: 0; }
.monitor-right { width: 280px; flex-shrink: 0; overflow-y: auto; padding: 10px; border-left: 1px solid rgba(255,255,255,0.06); }

.camera-panel { position: relative; background: #000; border-radius: 8px; overflow: hidden; max-height: 40vh; min-height: 200px; }
.camera-feed { width: 100%; height: 100%; object-fit: contain; }
.camera-offline { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 200px; gap: 12px; color: #909399; }
.det-bar { position: absolute; top: 8px; left: 8px; background: rgba(0,0,0,0.7); color: #67c23a; padding: 4px 12px; border-radius: 4px; font-size: 12px; font-family: monospace; }

.alerts-area { display: flex; flex-direction: column; gap: 3px; }

.events-panel, .records-panel, .attendance-panel { background: rgba(255,255,255,0.03); border-radius: 8px; padding: 10px; }
.events-panel h4, .records-panel h4, .attendance-panel h4 { margin: 0 0 8px 0; font-size: 14px; display: flex; align-items: center; gap: 6px; }

.record-list { display: flex; flex-direction: column; gap: 4px; }
.record-row { display: flex; align-items: center; gap: 6px; padding: 5px 8px; border-radius: 4px; background: rgba(255,255,255,0.03); font-size: 12px; }
.rec-name { font-weight: 600; min-width: 40px; }
.rec-time { margin-left: auto; color: #909399; font-family: monospace; }

.event-list { display: flex; flex-direction: column; gap: 3px; }
.event-row { display: flex; align-items: center; gap: 6px; padding: 4px 6px; border-radius: 4px; font-size: 11px; }
.event-ok { background: rgba(103,194,58,0.08); }
.event-warn { background: rgba(230,162,60,0.06); }
.evt-name { font-weight: 600; min-width: 50px; }
.evt-count { color: #909399; font-size: 10px; }
.evt-reason { color: #e6a23c; font-size: 10px; }
.evt-time { margin-left: auto; color: #909399; font-family: monospace; }

/* Attendance */
.summary-cards { margin-bottom: 8px; }
.sum-card { background: rgba(255,255,255,0.03); border-radius: 6px; padding: 10px 14px; }
.sum-title { font-size: 14px; font-weight: 600; margin-bottom: 6px; color: #409eff; }
.sum-row { font-size: 12px; line-height: 1.8; color: #c0c4cc; }
.sum-row b { color: #e0e0e0; }
.green { color: #67c23a; }
.red { color: #f56c6c; }

.rank-box { background: rgba(255,255,255,0.02); border-radius: 6px; padding: 8px; }
.rank-title { font-size: 12px; font-weight: 600; margin-bottom: 6px; color: #909399; }
.rank-row { display: flex; align-items: center; gap: 6px; padding: 3px 0; font-size: 11px; border-bottom: 1px solid rgba(255,255,255,0.03); }
.rank-row.rank-top { background: rgba(245,108,108,0.06); }
.rk-num { font-weight: 700; min-width: 24px; color: #f56c6c; }
.rk-name { font-weight: 600; min-width: 40px; }
.rk-dept { color: #909399; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rk-abs { font-weight: 600; color: #e6a23c; }
</style>

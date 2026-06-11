<template>
  <el-card shadow="never">
    <!-- 筛选区域 -->
    <el-form :inline="true" :model="filters" class="filter-form">
      <el-form-item label="操作人">
        <el-input v-model="filters.admin_name" placeholder="输入操作人" clearable style="width:160px" />
      </el-form-item>
      <el-form-item label="操作类型">
        <el-select v-model="filters.action" placeholder="全部类型" clearable style="width:180px">
          <el-option v-for="t in actionTypes" :key="t" :label="getActionLabel(t)" :value="t" />
        </el-select>
      </el-form-item>
      <el-form-item label="时间范围">
        <el-date-picker v-model="filters.dateRange" type="daterange" range-separator="至"
          start-placeholder="开始" end-placeholder="结束" value-format="YYYY-MM-DD"
          style="width:260px" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="fetchLogs">
          <el-icon><Search /></el-icon> 查询
        </el-button>
        <el-button @click="resetFilters">
          <el-icon><Refresh /></el-icon> 重置
        </el-button>
      </el-form-item>
    </el-form>

    <el-divider style="margin: 0 0 16px" />

    <!-- 日志表格 -->
    <el-table :data="logs" stripe border v-loading="loading"
      empty-text="暂无操作日志" max-height="calc(100vh - 340px)">
      <el-table-column type="index" label="#" width="50" align="center" />
      <el-table-column prop="admin_name" label="操作人" width="100" />
      <el-table-column label="操作类型" width="160">
        <template #default="{ row }">
          <el-tag :type="getActionTagType(row.action)" effect="dark" size="small">
            {{ getActionLabel(row.action) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="target_type" label="对象类型" width="100" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.target_type" size="small" type="info">{{ row.target_type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="target_name" label="操作对象" width="120" />
      <el-table-column prop="detail" label="详情" min-width="220" show-overflow-tooltip />
      <el-table-column prop="ip_address" label="IP地址" width="140" />
      <el-table-column label="操作时间" width="180">
        <template #default="{ row }">
          <span class="time-text">{{ formatTime(row.created_at) }}</span>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="table-footer">
      <el-pagination v-model:current-page="page" :page-size="perPage" :total="total"
        layout="total, prev, pager, next, jumper" background @current-change="fetchLogs" />
    </div>
  </el-card>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { getOperationLogs } from '../../api/index.js'

const loading = ref(false)
const logs = ref([])
const page = ref(1)
const perPage = ref(50)
const total = ref(0)
const actionTypes = ref([])

const filters = reactive({
  admin_name: '',
  action: '',
  dateRange: null
})

const actionLabelMap = {
  LOGIN: '管理员登录',
  LOGIN_FAILED: '登录失败',
  CREATE_MEMBER: '新增成员',
  UPDATE_MEMBER: '更新成员',
  DELETE_MEMBER: '删除成员',
  UPLOAD_FACE: '上传人脸',
  DELETE_FACE: '删除人脸',
  CHECK_IN: '签到',
  CHECK_OUT: '签退'
}

function getActionLabel(action) {
  return actionLabelMap[action] || action
}

function getActionTagType(action) {
  if (!action) return 'info'
  if (action.includes('FAILED') || action.includes('DELETE')) return 'danger'
  if (action.includes('CREATE') || action.includes('UPLOAD')) return 'success'
  if (action.includes('CHECK_IN')) return ''
  if (action.includes('CHECK_OUT')) return 'warning'
  if (action.includes('LOGIN')) return ''
  if (action.includes('UPDATE')) return 'primary'
  return 'info'
}

async function fetchLogs() {
  loading.value = true
  try {
    const params = { page: page.value, per_page: perPage.value }
    if (filters.admin_name) params.admin_name = filters.admin_name
    if (filters.action) params.action = filters.action
    if (filters.dateRange?.length === 2) {
      params.date_from = filters.dateRange[0]
      params.date_to = filters.dateRange[1]
    }
    const res = await getOperationLogs(params)
    logs.value = res.data.list
    total.value = res.data.total
  } catch { /* handled */ }
  finally { loading.value = false }
}

function resetFilters() {
  filters.admin_name = ''
  filters.action = ''
  filters.dateRange = null
  page.value = 1
  fetchLogs()
}

function formatTime(isoStr) {
  if (!isoStr) return ''
  const d = new Date(isoStr)
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

onMounted(() => {
  actionTypes.value = ['LOGIN', 'LOGIN_FAILED', 'CREATE_MEMBER', 'UPDATE_MEMBER', 'DELETE_MEMBER', 'UPLOAD_FACE', 'DELETE_FACE', 'CHECK_IN', 'CHECK_OUT', 'MANUAL_CHECKIN']
  fetchLogs()
})
</script>

<style scoped>
.filter-form {
  margin-bottom: 0;
}

.filter-form :deep(.el-form-item) {
  margin-bottom: 0;
}

.table-footer {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.time-text {
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
  font-size: 13px;
}
</style>

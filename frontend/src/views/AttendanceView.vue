<template>
  <el-card shadow="never">
    <template #header><span><el-icon><Clock /></el-icon> 考勤记录</span></template>
    <el-form :inline="true" class="filter-form">
      <el-form-item label="日期">
        <el-date-picker v-model="filters.dateRange" type="daterange" range-separator="至" start-placeholder="开始" end-placeholder="结束" value-format="YYYY-MM-DD" style="width:240px" />
      </el-form-item>
      <el-form-item label="类型">
        <el-select v-model="filters.check_type" clearable placeholder="全部" style="width:100px">
          <el-option label="签到" value="in"/><el-option label="签退" value="out"/>
        </el-select>
      </el-form-item>
      <el-form-item label="来源">
        <el-select v-model="filters.source" clearable placeholder="全部" style="width:120px">
          <el-option label="自动" value="auto"/><el-option label="人工" value="manual_admin"/>
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="fetchData"><el-icon><Search /></el-icon> 查询</el-button>
        <el-button @click="exportCSV"><el-icon><Download /></el-icon> 导出CSV</el-button>
        <el-button type="warning" @click="showManualDialog = true"><el-icon><Edit /></el-icon> 手工补录</el-button>
      </el-form-item>
    </el-form>
    <el-table :data="records" stripe border v-loading="loading" max-height="calc(100vh - 340px)">
      <el-table-column type="index" label="#" width="50" align="center"/>
      <el-table-column prop="member_name" label="姓名" width="100"/>
      <el-table-column prop="employee_id" label="工号" width="120"/>
      <el-table-column label="类型" width="80">
        <template #default="{row}"><el-tag :type="row.check_type==='in'?'success':'warning'" size="small" effect="dark">{{row.check_type==='in'?'签到':'签退'}}</el-tag></template>
      </el-table-column>
      <el-table-column label="时间" width="170"><template #default="{row}">{{formatTime(row.check_time)}}</template></el-table-column>
      <el-table-column prop="confidence" label="置信度" width="90"><template #default="{row}">{{(row.confidence*100).toFixed(1)}}%</template></el-table-column>
      <el-table-column label="来源" width="80"><template #default="{row}"><el-tag :type="row.source==='auto'?'':'info'" size="small">{{row.source==='auto'?'自动':'人工'}}</el-tag></template></el-table-column>
      <el-table-column prop="recognition_event_id" label="识别事件ID" width="110" align="center"/>
    </el-table>
    <div class="table-footer">
      <el-pagination v-model:current-page="page" :page-size="perPage" :total="total"
        layout="total, prev, pager, next" background @current-change="fetchData" />
    </div>

    <el-dialog v-model="showManualDialog" title="手工补录" width="400px" destroy-on-close>
      <el-form :model="manualForm" ref="manualFormRef">
        <el-form-item label="成员">
          <el-select v-model="manualForm.member_id" filterable placeholder="选择成员" style="width:100%">
            <el-option v-for="m in members" :key="m.id" :label="`${m.name}(${m.employee_id})`" :value="m.id"/>
          </el-select>
        </el-form-item>
        <el-form-item label="类型">
          <el-radio-group v-model="manualForm.check_type">
            <el-radio value="in">签到</el-radio><el-radio value="out">签退</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showManualDialog=false">取消</el-button>
        <el-button type="primary" :loading="manualLoading" @click="handleManual">确定</el-button>
      </template>
    </el-dialog>
  </el-card>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getCheckinRecords, manualCheckin, getMembers } from '../api/index.js'
const loading=ref(false),records=ref([]),page=ref(1),perPage=ref(30),total=ref(0)
const filters=reactive({dateRange:null,check_type:'',source:''})
const showManualDialog=ref(false),manualForm=reactive({member_id:null,check_type:'in'}),manualLoading=ref(false),members=ref([])
function formatTime(iso){if(!iso)return'';const d=new Date(iso),pad=n=>String(n).padStart(2,'0');return `${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`}
async function fetchData(){
  loading.value=true
  try{
    const params={page:page.value,per_page:perPage.value}
    if(filters.check_type)params.check_type=filters.check_type
    if(filters.source)params.source=filters.source
    if(filters.dateRange?.length===2){params.date_from=filters.dateRange[0];params.date_to=filters.dateRange[1]}
    const r=await getCheckinRecords(params);records.value=r.data.list;total.value=r.data.total
  }catch{}finally{loading.value=false}
}
function exportCSV(){
  const params={page:1,per_page:10000,format:'csv'}
  if(filters.check_type)params.check_type=filters.check_type
  if(filters.source)params.source=filters.source
  if(filters.dateRange?.length===2){params.date_from=filters.dateRange[0];params.date_to=filters.dateRange[1]}
  window.open(`/api/admin/checkin-records?${new URLSearchParams(params)}`,'_blank')
}
async function handleManual(){
  if(!manualForm.member_id){ElMessage.warning('请选择成员');return}
  manualLoading.value=true
  try{await manualCheckin(manualForm.member_id,manualForm.check_type);ElMessage.success('补录成功');showManualDialog.value=false;fetchData()}catch{}finally{manualLoading.value=false}
}
onMounted(async()=>{
  try{const r=await getMembers();members.value=r.data||[]}catch{}
  fetchData()
})
</script>
<style scoped>.filter-form{margin-bottom:0}.filter-form :deep(.el-form-item){margin-bottom:0}.table-footer{margin-top:16px;display:flex;justify-content:flex-end}</style>

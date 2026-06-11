<template>
  <el-card shadow="never">
    <template #header><span><el-icon><View /></el-icon> 识别事件</span></template>
    <el-table :data="events" stripe border v-loading="loading" max-height="calc(100vh - 280px)">
      <el-table-column prop="member_name" label="成员" width="100">
        <template #default="{row}"><span v-if="row.member_name">{{row.member_name}}</span><el-tag v-else type="info" size="small">未识别</el-tag></template>
      </el-table-column>
      <el-table-column label="匹配" width="80" align="center">
        <template #default="{row}"><el-tag :type="row.matched?'success':'danger'" size="small">{{row.matched?'成功':'失败'}}</el-tag></template>
      </el-table-column>
      <el-table-column prop="confidence" label="置信度" width="100">
        <template #default="{row}">{{(row.confidence*100).toFixed(1)}}%</template>
      </el-table-column>
      <el-table-column prop="distance" label="距离" width="80">
        <template #default="{row}">{{row.distance.toFixed(4)}}</template>
      </el-table-column>
      <el-table-column label="活体检测" width="100" align="center">
        <template #default="{row}">
          <el-tag v-if="row.liveness_passed===true" type="success" size="small">通过</el-tag>
          <el-tag v-else-if="row.liveness_passed===false" type="danger" size="small">未通过</el-tag>
          <el-tag v-else type="info" size="small">未开启</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="打卡" width="80" align="center">
        <template #default="{row}"><el-icon v-if="row.checkin_created" color="#67c23a"><CircleCheck /></el-icon><el-icon v-else color="#e6a23c"><Warning /></el-icon></template>
      </el-table-column>
      <el-table-column prop="failure_reason" label="失败原因" min-width="150" show-overflow-tooltip>
        <template #default="{row}">{{reasonLabel(row.failure_reason)}}</template>
      </el-table-column>
      <el-table-column label="时间" width="170">
        <template #default="{row}">{{formatTimeWrap(row.created_at)}}</template>
      </el-table-column>
    </el-table>
    <div class="table-footer">
      <el-pagination v-model:current-page="page" :page-size="perPage" :total="total"
        layout="total, prev, pager, next" background @current-change="fetchData" />
    </div>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getRecognitionEvents } from '../api/index.js'
import { formatTime, reasonLabel } from '../utils/index.js'
const loading=ref(false),events=ref([]),page=ref(1),perPage=ref(20),total=ref(0)
function formatTimeWrap(iso){return formatTime(iso,true)}
async function fetchData(){loading.value=true;try{const r=await getRecognitionEvents({page:page.value,per_page:perPage.value});events.value=r.data.list;total.value=r.data.total}catch{}finally{loading.value=false}}
onMounted(fetchData)
</script>
<style scoped>.table-footer{margin-top:16px;display:flex;justify-content:flex-end}</style>

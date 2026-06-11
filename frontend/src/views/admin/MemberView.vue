<template>
  <el-card shadow="never">
    <!-- 统计 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-statistic title="成员总数" :value="members.length" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="已录脸" :value="members.filter(m => m.has_face).length" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="正常" :value="members.filter(m => m.status === 1).length" />
      </el-col>
      <el-col :span="6">
        <el-statistic title="已禁用" :value="members.filter(m => m.status === 0).length" />
      </el-col>
    </el-row>

    <el-divider />

    <!-- 工具栏 -->
    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索姓名 / 工号 / 部门" clearable style="width:260px"
        :prefix-icon="Search" @clear="fetchMembers" @keyup.enter="fetchMembers" />
      <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width:120px"
        @change="fetchMembers">
        <el-option label="正常" :value="1" />
        <el-option label="禁用" :value="0" />
      </el-select>
      <el-button type="primary" @click="fetchMembers">
        <el-icon><Search /></el-icon> 搜索
      </el-button>
      <div class="toolbar-spacer" />
      <el-button type="success" @click="showAddDialog">
        <el-icon><Plus /></el-icon> 新增成员
      </el-button>
    </div>

    <!-- 成员表格 -->
    <el-table :data="pagedMembers" stripe border v-loading="loading" class="member-table"
      empty-text="暂无成员数据">
      <el-table-column type="index" label="#" width="50" align="center" />
      <el-table-column prop="name" label="姓名" width="100" />
      <el-table-column prop="employee_id" label="工号" width="120" />
      <el-table-column prop="department" label="部门" min-width="120" show-overflow-tooltip />
      <el-table-column prop="phone" label="电话" width="130" />
      <el-table-column label="人脸" width="90" align="center">
        <template #default="{ row }">
          <el-tag :type="row.has_face ? 'success' : 'info'" size="small" effect="dark">
            {{ row.has_face ? '已录入' : '未录入' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80" align="center">
        <template #default="{ row }">
          <el-switch :model-value="row.status === 1" size="small"
            active-text="启用" inactive-text="禁用"
            @change="toggleStatus(row)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right" align="center">
        <template #default="{ row }">
          <el-button text type="primary" size="small" @click="showEditDialog(row)">编辑</el-button>
          <el-button text type="warning" size="small" @click="showFaceDialog(row)">录脸</el-button>
          <el-popconfirm title="确定要删除该成员吗？" confirm-button-text="删除"
            cancel-button-text="取消" @confirm="handleDelete(row)">
            <template #reference>
              <el-button text type="danger" size="small">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="table-footer">
      <el-pagination v-model:current-page="page" v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]" :total="members.length"
        layout="total, sizes, prev, pager, next, jumper" background small />
    </div>
  </el-card>

  <!-- 新增/编辑对话框 -->
  <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑成员' : '新增成员'" width="500px"
    :close-on-click-modal="false" destroy-on-close>
    <el-form :model="form" :rules="formRules" ref="formRef" label-width="80px" status-icon>
      <el-form-item label="姓名" prop="name">
        <el-input v-model="form.name" placeholder="请输入姓名" :prefix-icon="User" />
      </el-form-item>
      <el-form-item label="工号" prop="employee_id">
        <el-input v-model="form.employee_id" placeholder="请输入工号" :disabled="isEdit"
          :prefix-icon="Tickets" />
      </el-form-item>
      <el-form-item label="部门">
        <el-input v-model="form.department" placeholder="请输入部门" :prefix-icon="OfficeBuilding" />
      </el-form-item>
      <el-form-item label="电话">
        <el-input v-model="form.phone" placeholder="请输入电话" :prefix-icon="Phone" />
      </el-form-item>
      <el-form-item label="邮箱">
        <el-input v-model="form.email" placeholder="请输入邮箱" :prefix-icon="Message" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取 消</el-button>
      <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确 定</el-button>
    </template>
  </el-dialog>

  <!-- 人脸录入对话框 -->
  <el-dialog v-model="faceDialogVisible" title="人脸录入" width="480px"
    :close-on-click-modal="false" destroy-on-close>
    <div v-if="currentMember" class="face-dialog">
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="姓名">{{ currentMember.name }}</el-descriptions-item>
        <el-descriptions-item label="工号">{{ currentMember.employee_id }}</el-descriptions-item>
      </el-descriptions>

      <el-divider />

      <el-upload class="face-uploader" drag :auto-upload="false"
        :show-file-list="false" accept="image/*" :on-change="handleFaceFileChange">
        <el-image v-if="facePreviewUrl" :src="facePreviewUrl" fit="contain"
          style="width:180px;height:180px;border-radius:8px" />
        <div v-else class="upload-empty">
          <el-icon :size="48" color="#c0c4cc"><UploadFilled /></el-icon>
          <p>点击或拖拽上传人脸照片</p>
          <span>请上传正面清晰单人照</span>
        </div>
      </el-upload>

      <div v-if="faceFile" class="upload-actions">
        <el-button type="primary" :loading="faceUploading" @click="handleFaceUpload" size="large">
          上传并提取人脸特征
        </el-button>
      </div>

      <el-alert v-if="currentMember.has_face" title="该成员已录入人脸，上传新照片将覆盖旧数据"
        type="warning" show-icon :closable="false" style="margin-top:16px" />
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getMembers, createMember, updateMember, deleteMember, uploadFace } from '../../api/index.js'

const loading = ref(false)
const members = ref([])
const keyword = ref('')
const filterStatus = ref(null)
const page = ref(1)
const pageSize = ref(20)

const pagedMembers = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return members.value.slice(start, start + pageSize.value)
})

// 弹窗
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitLoading = ref(false)
const formRef = ref(null)
const editingId = ref(null)

const form = reactive({ name: '', employee_id: '', department: '', phone: '', email: '' })
const formRules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  employee_id: [{ required: true, message: '请输入工号', trigger: 'blur' }]
}

// 人脸录入
const faceDialogVisible = ref(false)
const currentMember = ref(null)
const faceFile = ref(null)
const facePreviewUrl = ref('')
const faceUploading = ref(false)

async function fetchMembers() {
  loading.value = true
  try {
    const params = {}
    if (keyword.value) params.keyword = keyword.value
    if (filterStatus.value !== null) params.status = filterStatus.value
    const res = await getMembers(params)
    members.value = res.data
    page.value = 1
  } catch { /* handled */ }
  finally { loading.value = false }
}

function showAddDialog() {
  isEdit.value = false
  editingId.value = null
  Object.assign(form, { name: '', employee_id: '', department: '', phone: '', email: '' })
  dialogVisible.value = true
}

function showEditDialog(row) {
  isEdit.value = true
  editingId.value = row.id
  Object.assign(form, {
    name: row.name, employee_id: row.employee_id,
    department: row.department, phone: row.phone, email: row.email
  })
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitLoading.value = true
  try {
    const data = {
      name: form.name, employee_id: form.employee_id,
      department: form.department, phone: form.phone, email: form.email
    }
    if (isEdit.value) {
      await updateMember(editingId.value, data)
      ElMessage.success('成员信息已更新')
    } else {
      await createMember(data)
      ElMessage.success('成员创建成功')
    }
    dialogVisible.value = false
    fetchMembers()
  } catch { /* handled */ }
  finally { submitLoading.value = false }
}

async function handleDelete(row) {
  try {
    await deleteMember(row.id)
    ElMessage.success('成员已删除')
    fetchMembers()
  } catch { /* handled */ }
}

async function toggleStatus(row) {
  const newStatus = row.status === 1 ? 0 : 1
  try {
    await updateMember(row.id, { status: newStatus })
    row.status = newStatus
    ElMessage.success(newStatus === 1 ? '已启用' : '已禁用')
  } catch { /* handled */ }
}

function showFaceDialog(row) {
  currentMember.value = { ...row }
  faceFile.value = null
  facePreviewUrl.value = ''
  faceDialogVisible.value = true
}

function handleFaceFileChange(file) {
  faceFile.value = file.raw
  const reader = new FileReader()
  reader.onload = (e) => { facePreviewUrl.value = e.target.result }
  reader.readAsDataURL(file.raw)
}

async function handleFaceUpload() {
  if (!faceFile.value) {
    ElMessage.warning('请先选择人脸照片')
    return
  }
  faceUploading.value = true
  try {
    await uploadFace(currentMember.value.id, faceFile.value)
    ElMessage.success('人脸录入成功')
    faceDialogVisible.value = false
    fetchMembers()
  } catch { /* handled */ }
  finally { faceUploading.value = false }
}

onMounted(fetchMembers)
</script>

<style scoped>
.stats-row {
  margin-bottom: 4px;
}

.toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.toolbar-spacer {
  flex: 1;
}

.table-footer {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.face-dialog {
  text-align: center;
}

.face-uploader {
  display: inline-block;
}

.face-uploader :deep(.el-upload-dragger) {
  width: 240px;
  height: 240px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #999;
}

.upload-empty span {
  font-size: 12px;
  color: #c0c4cc;
}

.upload-actions {
  margin-top: 16px;
}
</style>

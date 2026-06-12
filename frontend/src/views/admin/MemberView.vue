<template>
  <el-card shadow="never">
    <!-- 工具栏 -->
    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索姓名/学号/班级" clearable style="width:240px"
        :prefix-icon="Search" @clear="fetchMembers" @keyup.enter="fetchMembers" />
      <el-button type="primary" @click="fetchMembers"><el-icon><Search /></el-icon> 搜索</el-button>
      <div class="toolbar-spacer" />
      <el-button type="success" @click="showAddDialog"><el-icon><Plus /></el-icon> 新增成员</el-button>
    </div>

    <!-- 成员表格 -->
    <el-table :data="pagedMembers" stripe border v-loading="loading" empty-text="暂无成员">
      <el-table-column type="index" label="#" width="50" align="center" />
      <el-table-column prop="name" label="姓名" width="100" />
      <el-table-column prop="employee_id" label="学号" width="100" />
      <el-table-column prop="department" label="班级" min-width="100" show-overflow-tooltip />
      <el-table-column label="人脸样本" width="160" align="center">
        <template #default="{ row }">
          <div class="sample-cell">
            <span class="sample-count">{{ row.sample_count || 0 }} / {{ maxSamples }}</span>
            <el-tag v-if="row.sample_count >= 3" type="success" size="small" effect="dark">可识别</el-tag>
            <el-tag v-else-if="row.sample_count > 0" type="warning" size="small" effect="dark">不足</el-tag>
            <el-tag v-else type="info" size="small">未录入</el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="80" align="center">
        <template #default="{ row }">
          <el-switch :model-value="row.active" size="small" active-text="启用" inactive-text="禁用"
            @change="toggleActive(row)" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="240" fixed="right" align="center">
        <template #default="{ row }">
          <el-button text type="primary" size="small" @click="showEditDialog(row)">编辑</el-button>
          <el-button text type="warning" size="small" @click="showFaceDialog(row)">录脸</el-button>
          <el-popconfirm title="确定删除该成员？" @confirm="handleDelete(row)">
            <template #reference>
              <el-button text type="danger" size="small">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

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
        <el-input v-model="form.name" placeholder="请输入姓名" />
      </el-form-item>
      <el-form-item label="学号" prop="employee_id">
        <el-input v-model="form.employee_id" placeholder="请输入学号" :disabled="isEdit" />
      </el-form-item>
      <el-form-item label="班级">
        <el-input v-model="form.department" placeholder="请输入班级" />
      </el-form-item>
      <el-form-item label="电话">
        <el-input v-model="form.phone" placeholder="请输入电话" />
      </el-form-item>
      <el-form-item label="邮箱">
        <el-input v-model="form.email" placeholder="请输入邮箱" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取 消</el-button>
      <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确 定</el-button>
    </template>
  </el-dialog>

  <!-- 人脸录入对话框 -->
  <el-dialog v-model="faceDialogVisible" title="人脸录入" width="600px"
    :close-on-click-modal="false" destroy-on-close @opened="loadSamples">
    <div v-if="currentMember" class="face-dialog">
      <el-descriptions :column="2" border size="small">
        <el-descriptions-item label="姓名">{{ currentMember.name }}</el-descriptions-item>
        <el-descriptions-item label="学号">{{ currentMember.employee_id }}</el-descriptions-item>
      </el-descriptions>

      <el-divider />

      <!-- 已有样本列表 -->
      <div v-if="existingSamples.length > 0" class="samples-section">
        <h4>已上传样本 ({{ existingSamples.length }}/{{ maxSamples }})</h4>
        <el-alert v-if="existingSamples.length < 3" title="样本不足，需要至少3张才能参与无感识别"
          type="warning" show-icon :closable="false" style="margin-bottom:12px" />
        <div class="samples-grid">
          <div v-for="s in existingSamples" :key="s.id" class="sample-item">
            <img :src="sampleImageUrl(s.image_path)" class="sample-thumb" />
            <el-button text type="danger" size="small" class="sample-del"
              @click="deleteSample(s.id)"><el-icon><Delete /></el-icon></el-button>
          </div>
        </div>
      </div>
      <el-empty v-else description="还没有人脸样本" :image-size="60" />

      <el-divider />

      <!-- 上传区域 -->
      <h4>上传新样本</h4>
      <el-alert v-if="existingSamples.length >= maxSamples" title="已达到最大样本数" type="info" :closable="false" style="margin-bottom:12px" />
      <div v-else class="upload-area">
        <el-upload class="face-uploader" drag multiple
          :auto-upload="false" :show-file-list="false"
          accept="image/*" :on-change="handleFaceSelect"
          :before-upload="() => false">
          <div class="upload-box">
            <img v-if="facePreviewUrl" :src="facePreviewUrl" class="preview-img" />
            <div v-else class="upload-placeholder">
              <el-icon :size="40" color="#c0c4cc"><UploadFilled /></el-icon>
              <p>拖拽或点击选择照片</p>
              <span>支持从微信窗口拖入</span>
            </div>
          </div>
        </el-upload>
        <div v-if="pendingFiles.length > 0" style="margin-top:12px">
          <el-tag v-for="(f, i) in pendingFiles" :key="i" closable @close="pendingFiles.splice(i,1)" style="margin:2px">
            {{ f.name }}
          </el-tag>
        </div>
        <el-button v-if="pendingFiles.length > 0" type="primary" :loading="faceUploading"
          @click="uploadPending" style="margin-top:12px" :disabled="existingSamples.length + pendingFiles.length > maxSamples">
          上传 {{ pendingFiles.length }} 张样本
        </el-button>
        <el-button v-else-if="faceFile" type="primary" :loading="faceUploading"
          @click="uploadPending" style="margin-top:12px">
          上传样本
        </el-button>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getMembers, createMember, updateMember, deleteMember, uploadFaceSample, getFaceSamples, deleteFaceSample } from '../../api/index.js'

const loading = ref(false)
const members = ref([])
const keyword = ref('')
const page = ref(1)
const pageSize = ref(20)
const maxSamples = 5

const pagedMembers = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return members.value.slice(start, start + pageSize.value)
})

const dialogVisible = ref(false)
const isEdit = ref(false)
const submitLoading = ref(false)
const formRef = ref(null)
const editingId = ref(null)
const form = reactive({ name: '', employee_id: '', department: '', phone: '', email: '' })
const formRules = {
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  employee_id: [{ required: true, message: '请输入学号', trigger: 'blur' }]
}

const faceDialogVisible = ref(false)
const currentMember = ref(null)
const faceFile = ref(null)
const facePreviewUrl = ref('')
const faceUploading = ref(false)
const existingSamples = ref([])
const pendingFiles = ref([])

async function fetchMembers() {
  loading.value = true
  try {
    const params = {}
    if (keyword.value) params.keyword = keyword.value
    const res = await getMembers(params)
    members.value = res.data || []
    page.value = 1
  } catch {} finally { loading.value = false }
}

function showAddDialog() {
  isEdit.value = false; editingId.value = null
  Object.assign(form, { name: '', employee_id: '', department: '', phone: '', email: '' })
  dialogVisible.value = true
}

function showEditDialog(row) {
  isEdit.value = true; editingId.value = row.id
  Object.assign(form, { name: row.name, employee_id: row.employee_id, department: row.department, phone: row.phone, email: row.email })
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitLoading.value = true
  try {
    const data = { name: form.name, employee_id: form.employee_id, department: form.department, phone: form.phone, email: form.email }
    if (isEdit.value) { await updateMember(editingId.value, data); ElMessage.success('已更新') }
    else { await createMember(data); ElMessage.success('已创建') }
    dialogVisible.value = false; fetchMembers()
  } catch {} finally { submitLoading.value = false }
}

async function handleDelete(row) {
  try { await deleteMember(row.id); ElMessage.success('已删除'); fetchMembers() } catch {}
}

async function toggleActive(row) {
  try {
    await updateMember(row.id, { active: !row.active })
    row.active = !row.active
    ElMessage.success(row.active ? '已启用' : '已禁用')
  } catch {}
}

function showFaceDialog(row) {
  currentMember.value = { ...row }
  faceFile.value = null
  facePreviewUrl.value = ''
  pendingFiles.value = []
  existingSamples.value = []
  faceDialogVisible.value = true
}

async function loadSamples() {
  if (!currentMember.value) return
  try {
    const res = await getFaceSamples(currentMember.value.id)
    existingSamples.value = res.data || []
  } catch {}
}

function handleFaceSelect(file) {
  faceFile.value = file.raw
  // 添加到队列
  const exists = pendingFiles.value.find(f => f.name === file.name && f.size === file.size)
  if (!exists) pendingFiles.value.push(file.raw)
  // 预览
  const reader = new FileReader()
  reader.onload = (e) => { facePreviewUrl.value = e.target.result }
  reader.readAsDataURL(file.raw)
}

async function uploadPending() {
  if (pendingFiles.value.length === 0 && !faceFile.value) return
  const files = pendingFiles.value.length > 0 ? [...pendingFiles.value] : [faceFile.value]
  let success = 0
  faceUploading.value = true
  for (const f of files) {
    try {
      await uploadFaceSample(currentMember.value.id, f)
      success++
    } catch {}
  }
  faceUploading.value = false
  if (success > 0) {
    ElMessage.success(`成功上传 ${success} 张样本`)
    pendingFiles.value = []
    faceFile.value = null
    facePreviewUrl.value = ''
    await loadSamples()
    fetchMembers()
  }
}

async function deleteSample(sid) {
  try {
    await deleteFaceSample(sid)
    ElMessage.success('已删除')
    await loadSamples()
    fetchMembers()
  } catch {}
}

function sampleImageUrl(imagePath) {
  const token = localStorage.getItem('admin_token') || ''
  return `/uploads/${encodeURIComponent(imagePath)}?token=${encodeURIComponent(token)}`
}

onMounted(fetchMembers)
</script>

<style scoped>
.toolbar { display: flex; gap: 10px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
.toolbar-spacer { flex: 1; }
.table-footer { margin-top: 16px; display: flex; justify-content: flex-end; }
.face-dialog { text-align: left; }
.sample-cell { display: flex; align-items: center; gap: 6px; justify-content: center; }
.sample-count { font-weight: 600; font-size: 14px; }
.samples-section h4 { margin: 0 0 8px 0; font-size: 14px; }
.samples-grid { display: flex; gap: 8px; flex-wrap: wrap; }
.sample-item { position: relative; width: 80px; height: 80px; border-radius: 6px; overflow: hidden; border: 1px solid #e4e7ed; }
.sample-thumb { width: 100%; height: 100%; object-fit: cover; }
.sample-del { position: absolute; top: 0; right: 0; background: rgba(0,0,0,0.5); padding: 2px; }
.upload-area { text-align: center; }
.face-uploader { display: inline-block; width: 100%; }
.face-uploader :deep(.el-upload-dragger) {
  width: 100% !important;
  height: 200px !important;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
}
.upload-box { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; overflow: hidden; }
.preview-img { max-width: 100%; max-height: 100%; object-fit: contain; }
.upload-placeholder { text-align: center; color: #999; }
.upload-placeholder p { margin: 8px 0 4px; font-size: 14px; }
.upload-placeholder span { font-size: 12px; color: #c0c4cc; }
</style>

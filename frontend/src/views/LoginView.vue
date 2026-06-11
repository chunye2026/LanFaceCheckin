<template>
  <div class="login-wrapper">
    <el-card class="login-card" shadow="always">
      <template #header>
        <div class="card-header">
          <el-icon :size="40" color="#409eff"><Camera /></el-icon>
          <h2>无感考勤系统</h2>
          <p class="subtitle">管理后台</p>
        </div>
      </template>
      <el-form :model="form" :rules="rules" ref="formRef" label-position="top" size="large" @keyup.enter="handleLogin">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="管理员用户名" :prefix-icon="User" clearable />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="管理员密码" :prefix-icon="Lock" show-password clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleLogin" class="login-btn">登 录</el-button>
        </el-form-item>
      </el-form>
      <div class="card-footer">
        <el-divider />
        <el-link :underline="false" @click="$router.push('/')"><el-icon><ArrowLeft /></el-icon> 返回监控大屏</el-link>
      </div>
    </el-card>

    <el-dialog v-model="showChangePwd" title="首次登录，请修改密码" :close-on-click-modal="false" :close-on-press-escape="false" width="400px">
      <el-form :model="pwdForm" ref="pwdFormRef" label-width="100px">
        <el-form-item label="新密码" prop="new_password" :rules="[{required:true,message:'至少6位',min:6}]">
          <el-input v-model="pwdForm.new_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm" :rules="[{required:true,validator:validateConfirm,trigger:'blur'}]">
          <el-input v-model="pwdForm.confirm" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button type="primary" :loading="changingPwd" @click="handleChangePwd">确认修改</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login, changePassword } from '../api/index.js'

const router = useRouter()
const formRef = ref(null), loading = ref(false)
const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const showChangePwd = ref(false), changingPwd = ref(false)
const pwdForm = reactive({ new_password: '', confirm: '' })
const pwdFormRef = ref(null)

function validateConfirm(rule, value, callback) {
  if (value !== pwdForm.new_password) callback(new Error('两次密码不一致'))
  else callback()
}

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    const res = await login(form.username, form.password)
    localStorage.setItem('admin_token', res.data.token)
    localStorage.setItem('admin_username', res.data.username)
    if (res.data.must_change_password) {
      showChangePwd.value = true
    } else {
      ElMessage.success('登录成功')
      router.push('/admin/dashboard')
    }
  } catch {} finally { loading.value = false }
}

async function handleChangePwd() {
  const valid = await pwdFormRef.value.validate().catch(() => false)
  if (!valid) return
  changingPwd.value = true
  try {
    await changePassword(form.password, pwdForm.new_password)
    ElMessage.success('密码修改成功')
    showChangePwd.value = false
    router.push('/admin/dashboard')
  } catch {} finally { changingPwd.value = false }
}
</script>

<style scoped>
.login-wrapper{min-height:100vh;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);padding:20px}
.login-card{width:420px;border-radius:12px}
.login-card :deep(.el-card__header){padding:30px 30px 0;border-bottom:none}
.login-card :deep(.el-card__body){padding:10px 30px 30px}
.card-header{text-align:center}.card-header h2{margin:12px 0 4px;font-size:22px;color:#333}
.subtitle{color:#999;font-size:14px;margin:0}.login-btn{width:100%}
.card-footer{text-align:center}.card-footer .el-divider{margin:0 0 16px}
</style>

<template>
  <div class="login-wrapper">
    <el-card class="login-card" shadow="always">
      <template #header>
        <div class="card-header">
          <el-icon :size="40" color="#409eff"><Camera /></el-icon>
          <h2>人脸识别打卡系统</h2>
          <p class="subtitle">管理后台</p>
        </div>
      </template>

      <el-form :model="form" :rules="rules" ref="formRef" label-position="top" size="large"
        @keyup.enter="handleLogin">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入管理员用户名"
            :prefix-icon="User" clearable />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码"
            :prefix-icon="Lock" show-password clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleLogin" class="login-btn">
            登 录
          </el-button>
        </el-form-item>
      </el-form>

      <div class="card-footer">
        <el-divider />
        <el-link :underline="false" @click="$router.push('/')">
          <el-icon><ArrowLeft /></el-icon> 返回打卡页面
        </el-link>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '../../api/index.js'

const router = useRouter()
const formRef = ref(null)
const loading = ref(false)

const form = reactive({ username: '', password: '' })

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function handleLogin() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const res = await login(form.username, form.password)
    localStorage.setItem('admin_token', res.data.token)
    localStorage.setItem('admin_username', res.data.username)
    ElMessage.success('登录成功')
    router.push('/admin/members')
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrapper {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  padding: 20px;
}

.login-card {
  width: 420px;
  border-radius: 12px;
}

.login-card :deep(.el-card__header) {
  padding: 30px 30px 0;
  border-bottom: none;
}

.login-card :deep(.el-card__body) {
  padding: 10px 30px 30px;
}

.card-header {
  text-align: center;
}

.card-header h2 {
  margin: 12px 0 4px;
  font-size: 22px;
  color: #333;
}

.subtitle {
  color: #999;
  font-size: 14px;
  margin: 0;
}

.login-btn {
  width: 100%;
}

.card-footer {
  text-align: center;
}

.card-footer .el-divider {
  margin: 0 0 16px;
}
</style>

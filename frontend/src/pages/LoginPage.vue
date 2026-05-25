<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  NForm,
  NFormItem,
  NInput,
  NButton,
  NTabs,
  NTabPane,
  NSpace,
  NAlert,
  useMessage,
} from 'naive-ui'
import { authApi, setToken } from '@/api/client'

const router = useRouter()
const message = useMessage()

const activeTab = ref('login')
const loading = ref(false)
const error = ref('')

// Login form
const loginForm = ref({ username: '', password: '' })

// Register form
const registerForm = ref({ username: '', email: '', password: '', confirmPassword: '' })

async function handleLogin() {
  error.value = ''
  if (!loginForm.value.username || !loginForm.value.password) {
    error.value = '请填写用户名和密码'
    return
  }
  loading.value = true
  try {
    const res = await authApi.login(loginForm.value)
    setToken(res.data.access_token)
    message.success('登录成功')
    router.push('/dashboard')
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err?.response?.data?.detail || '登录失败，请检查用户名和密码'
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  error.value = ''
  const { username, email, password, confirmPassword } = registerForm.value
  if (!username || !password) {
    error.value = '请填写用户名和密码'
    return
  }
  if (password !== confirmPassword) {
    error.value = '两次输入的密码不一致'
    return
  }
  if (password.length < 6) {
    error.value = '密码长度至少6位'
    return
  }
  loading.value = true
  try {
    const res = await authApi.register({
      username,
      email: email || undefined,
      password,
    })
    setToken(res.data.access_token)
    message.success('注册成功')
    router.push('/profile')
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    error.value = err?.response?.data?.detail || '注册失败，请稍后再试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="brand">
        <h1>JavaScript 个性化学习平台</h1>
        <p>基于大模型的多智能体学习系统</p>
      </div>

      <NAlert v-if="error" type="error" :title="error" style="margin-bottom: 16px" />

      <NTabs v-model:value="activeTab" type="line" animated>
        <NTabPane name="login" tab="登录">
          <NForm @submit.prevent="handleLogin">
            <NFormItem label="用户名">
              <NInput
                v-model:value="loginForm.username"
                placeholder="输入用户名"
                size="large"
                :disabled="loading"
              />
            </NFormItem>
            <NFormItem label="密码">
              <NInput
                v-model:value="loginForm.password"
                type="password"
                placeholder="输入密码"
                size="large"
                :disabled="loading"
                @keyup.enter="handleLogin"
              />
            </NFormItem>
            <NButton
              type="primary"
              size="large"
              block
              :loading="loading"
              @click="handleLogin"
            >
              登录
            </NButton>
          </NForm>
        </NTabPane>

        <NTabPane name="register" tab="注册">
          <NForm @submit.prevent="handleRegister">
            <NFormItem label="用户名">
              <NInput
                v-model:value="registerForm.username"
                placeholder="3-20个字符"
                size="large"
                :disabled="loading"
              />
            </NFormItem>
            <NFormItem label="邮箱（选填）">
              <NInput
                v-model:value="registerForm.email"
                placeholder="your@email.com"
                size="large"
                :disabled="loading"
              />
            </NFormItem>
            <NFormItem label="密码">
              <NInput
                v-model:value="registerForm.password"
                type="password"
                placeholder="至少6位"
                size="large"
                :disabled="loading"
              />
            </NFormItem>
            <NFormItem label="确认密码">
              <NInput
                v-model:value="registerForm.confirmPassword"
                type="password"
                placeholder="再次输入密码"
                size="large"
                :disabled="loading"
                @keyup.enter="handleRegister"
              />
            </NFormItem>
            <NButton
              type="primary"
              size="large"
              block
              :loading="loading"
              @click="handleRegister"
            >
              注册并开始学习
            </NButton>
          </NForm>
        </NTabPane>
      </NTabs>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 420px;
  padding: 32px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.brand {
  text-align: center;
  margin-bottom: 24px;
}

.brand h1 {
  margin: 0;
  font-size: 22px;
  color: #333;
}

.brand p {
  margin: 8px 0 0;
  font-size: 14px;
  color: #999;
}
</style>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NSpace, NSpin } from 'naive-ui'
import type { StudentProfile } from '@/types'
import { profileApi, conversationApi } from '@/api/client'
import DimensionGrid from '@/components/profile/DimensionGrid.vue'

const router = useRouter()
const profile = ref<StudentProfile | null>(null)
const loading = ref(true)

onMounted(async () => {
  await loadProfile()
})

async function loadProfile() {
  loading.value = true
  try {
    const res = await profileApi.get()
    profile.value = res.data
  } catch {
    profile.value = null
  } finally {
    loading.value = false
  }
}

async function startAssessment() {
  try {
    const res = await conversationApi.create('profile_building', '学习画像评估')
    router.push(`/conversations/${res.data.id}`)
  } catch {
    // Handle error silently
    console.error('Failed to create assessment conversation')
  }
}
</script>

<template>
  <div class="profile-page">
    <div class="header">
      <h2>学习画像</h2>
      <NSpace>
        <NButton v-if="profile?.profileConfidence && profile.profileConfidence > 0" @click="loadProfile">
          刷新
        </NButton>
        <NButton type="primary" @click="startAssessment">
          {{ profile?.profileConfidence ? '更新画像' : '开始画像评估' }}
        </NButton>
      </NSpace>
    </div>

    <NSpin v-if="loading" class="loading" />

    <div v-else-if="!profile || profile.profileConfidence === 0" class="empty-state">
      <div class="empty-icon">&#128218;</div>
      <h3>尚未建立学习画像</h3>
      <p>通过与 AI 智能体对话，系统将了解你的 JavaScript 知识水平，建立个性化学习画像。</p>
      <NButton size="large" type="primary" @click="startAssessment">
        开始画像评估
      </NButton>
    </div>

    <DimensionGrid v-else :profile="profile" />
  </div>
</template>

<style scoped>
.profile-page {
  padding: 24px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header h2 {
  margin: 0;
}

.loading {
  display: flex;
  justify-content: center;
  margin-top: 80px;
}

.empty-state {
  text-align: center;
  margin-top: 80px;
  color: #666;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-state h3 {
  margin: 0 0 8px;
  color: #333;
}

.empty-state p {
  max-width: 400px;
  margin: 0 auto 24px;
  line-height: 1.6;
}
</style>

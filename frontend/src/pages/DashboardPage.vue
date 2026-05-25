<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  NCard,
  NGrid,
  NGi,
  NStatistic,
  NButton,
  NSpin,
  NTag,
  NProgress,
  NSpace,
} from 'naive-ui'
import { evaluationApi, profileApi, pathApi, conversationApi } from '@/api/client'

const router = useRouter()
const loading = ref(true)
const stats = ref({
  profile_confidence: 0,
  active_path: null as { title: string; progress: number; total_nodes: number; completed_nodes: number } | null,
  recent_activities_7d: 0,
  total_resources: 0,
  total_exercises: 0,
})
const hasProfile = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const [dashRes, profileRes] = await Promise.allSettled([
      evaluationApi.getDashboard(),
      profileApi.get(),
    ])
    if (dashRes.status === 'fulfilled') {
      stats.value = dashRes.value.data
    }
    if (profileRes.status === 'fulfilled') {
      hasProfile.value = true
    }
  } catch {
    // Dashboard might fail if no data yet — that's OK
  } finally {
    loading.value = false
  }
})

async function startProfileAssessment() {
  try {
    const res = await conversationApi.create('profile_building', '画像评估')
    router.push(`/conversations/${res.data.id}`)
  } catch {
    // handled
  }
}

async function startTutoring() {
  try {
    const res = await conversationApi.create('tutoring', 'JavaScript学习辅导')
    router.push(`/conversations/${res.data.id}`)
  } catch {
    // handled
  }
}

async function generatePath() {
  try {
    const res = await pathApi.generate({ learning_goal: '系统掌握JavaScript核心知识' })
    const path = res.data
    if (path?.path_id) {
      router.push(`/learning-path/${path.path_id}`)
    }
  } catch {
    // handled
  }
}
</script>

<template>
  <div class="dashboard">
    <div class="header">
      <h2>学习仪表盘</h2>
    </div>

    <NSpin v-if="loading" class="loading" />

    <!-- Quick actions (no profile yet) -->
    <div v-if="!loading && !hasProfile" class="welcome-banner">
      <h3>欢迎来到 JavaScript 个性化学习平台</h3>
      <p>开始你的编程学习之旅吧</p>
      <NSpace>
        <NButton size="large" type="primary" @click="startProfileAssessment">
          开始画像评估
        </NButton>
        <NButton size="large" @click="startTutoring">
          直接提问
        </NButton>
      </NSpace>
    </div>

    <template v-else>
      <!-- Stats grid -->
      <NGrid :cols="4" :x-gap="16" :y-gap="16" style="margin-bottom: 24px">
        <NGi>
          <NCard>
            <NStatistic label="画像置信度" :value="`${(stats.profile_confidence * 100).toFixed(0)}%`" />
          </NCard>
        </NGi>
        <NGi>
          <NCard>
            <NStatistic label="本周活动" :value="stats.recent_activities_7d" />
          </NCard>
        </NGi>
        <NGi>
          <NCard>
            <NStatistic label="生成资源" :value="stats.total_resources" />
          </NCard>
        </NGi>
        <NGi>
          <NCard>
            <NStatistic label="练习提交" :value="stats.total_exercises" />
          </NCard>
        </NGi>
      </NGrid>

      <!-- Active path -->
      <NGrid :cols="2" :x-gap="16" :y-gap="16">
        <NGi>
          <NCard title="学习路径" size="small">
            <template v-if="stats.active_path" #header-extra>
              <NTag type="info">进行中</NTag>
            </template>
            <div v-if="stats.active_path">
              <p style="margin: 0 0 12px; font-weight: 500">{{ stats.active_path.title }}</p>
              <NProgress
                type="line"
                :percentage="Math.round(stats.active_path.progress)"
                :height="20"
                :border-radius="4"
              />
              <p style="margin: 8px 0 0; color: #999; font-size: 13px">
                {{ stats.active_path.completed_nodes }} / {{ stats.active_path.total_nodes }} 个节点完成
              </p>
            </div>
            <div v-else class="empty-block">
              <p>尚未生成学习路径</p>
              <NButton size="small" type="primary" @click="generatePath">生成路径</NButton>
            </div>
          </NCard>
        </NGi>

        <NGi>
          <NCard title="快捷入口" size="small">
            <NSpace vertical>
              <NButton block @click="startTutoring">AI 辅导答疑</NButton>
              <NButton block @click="startProfileAssessment">更新学习画像</NButton>
              <NButton block @click="generatePath">重新规划路径</NButton>
            </NSpace>
          </NCard>
        </NGi>
      </NGrid>
    </template>
  </div>
</template>

<style scoped>
.dashboard {
  padding: 24px;
}

.header {
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

.welcome-banner {
  text-align: center;
  margin-top: 80px;
  padding: 48px;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border-radius: 16px;
}

.welcome-banner h3 {
  margin: 0 0 8px;
  font-size: 22px;
}

.welcome-banner p {
  color: #666;
  margin: 0 0 24px;
}

.empty-block {
  text-align: center;
  padding: 24px;
}

.empty-block p {
  color: #999;
  margin: 0 0 12px;
}
</style>

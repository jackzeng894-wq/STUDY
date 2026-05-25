<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NCard, NButton, NTag, NSpin, NEmpty, NProgress, NSpace, NModal, NInput } from 'naive-ui'
import { pathApi } from '@/api/client'

const router = useRouter()
const paths = ref<{ id: string; title: string | null; status: string; totalNodes: number; completedNodes: number; version: number }[]>([])
const loading = ref(true)
const showGenerate = ref(false)
const goalInput = ref('系统掌握JavaScript核心知识')

const statusLabels: Record<string, string> = { active: '进行中', completed: '已完成', paused: '已暂停', superseded: '已更新' }
const statusColors: Record<string, string> = { active: 'info', completed: 'success', paused: 'warning', superseded: 'default' }

onMounted(async () => { await loadPaths() })

async function loadPaths() {
  loading.value = true
  try { const res = await pathApi.list(); paths.value = res.data.items || [] } catch { paths.value = [] }
  finally { loading.value = false }
}

async function generatePath() {
  try {
    const res = await pathApi.generate({ learning_goal: goalInput.value })
    showGenerate.value = false
    if (res.data?.path_id) router.push(`/learning-path/${res.data.path_id}`)
    else await loadPaths()
  } catch { /* handled */ }
}
</script>

<template>
  <div style="padding: 24px">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px">
      <h2 style="margin: 0">学习路径</h2>
      <NButton type="primary" @click="showGenerate = true">生成新路径</NButton>
    </div>
    <NSpin v-if="loading" style="display: flex; justify-content: center; margin-top: 80px" />
    <NEmpty v-else-if="paths.length === 0" description="还没有学习路径">
      <template #extra><NButton type="primary" @click="showGenerate = true">生成路径</NButton></template>
    </NEmpty>
    <div v-else style="display: grid; gap: 12px">
      <NCard v-for="p in paths" :key="p.id" hoverable @click="router.push(`/learning-path/${p.id}`)">
        <template #header>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <span style="font-weight: 500">{{ p.title || '学习路径' }}</span>
            <NTag :type="(statusColors[p.status] as never) || 'default'" size="small">{{ statusLabels[p.status] || p.status }}</NTag>
          </div>
        </template>
        <NProgress v-if="p.totalNodes > 0" :percentage="Math.round(p.completedNodes / p.totalNodes * 100)" :height="16" :border-radius="4" />
        <p style="font-size: 12px; color: #999; margin: 8px 0 0">{{ p.completedNodes }} / {{ p.totalNodes }} 节点 · v{{ p.version }}</p>
      </NCard>
    </div>
    <NModal v-model:show="showGenerate" title="生成学习路径" preset="card" style="width: 420px">
      <NSpace vertical>
        <NInput v-model:value="goalInput" placeholder="学习目标" size="large" />
        <NButton type="primary" block size="large" @click="generatePath">开始生成</NButton>
      </NSpace>
    </NModal>
  </div>
</template>

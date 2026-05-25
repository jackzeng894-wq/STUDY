<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NCard, NTag, NSpin, NEmpty, NSelect, NSpace } from 'naive-ui'
import { resourceApi } from '@/api/client'

const router = useRouter()
const resources = ref<{ id: string; resourceType: string; title: string; difficulty: string; reviewStatus: string; createdAt: string }[]>([])
const loading = ref(true)
const filterType = ref('')
const filterDifficulty = ref('')

const typeLabels: Record<string, string> = {
  course_doc: '文档', mind_map: '思维导图', exercise: '练习', code_case: '代码案例',
  ppt: 'PPT', project: '项目', reading: '阅读', video_script: '动画脚本',
}
const diffColors: Record<string, string> = { beginner: 'success', intermediate: 'warning', advanced: 'error' }

onMounted(async () => { await loadResources() })

async function loadResources() {
  loading.value = true
  try {
    const params: Record<string, string> = {}
    if (filterType.value) params.resource_type = filterType.value
    if (filterDifficulty.value) params.difficulty = filterDifficulty.value
    const res = await resourceApi.list(params)
    resources.value = res.data.items || []
  } catch { resources.value = [] }
  finally { loading.value = false }
}
</script>

<template>
  <div style="padding: 24px">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px">
      <h2 style="margin: 0">资源库</h2>
    </div>
    <NSpace style="margin-bottom: 16px">
      <NSelect v-model:value="filterType" :options="[
        { label: '全部类型', value: '' },
        ...Object.entries(typeLabels).map(([k, v]) => ({ label: v, value: k })),
      ]" placeholder="资源类型" clearable style="width: 140px" @update:value="loadResources" />
      <NSelect v-model:value="filterDifficulty" :options="[
        { label: '全部难度', value: '' },
        { label: '入门', value: 'beginner' },
        { label: '中级', value: 'intermediate' },
        { label: '高级', value: 'advanced' },
      ]" placeholder="难度" clearable style="width: 120px" @update:value="loadResources" />
    </NSpace>
    <NSpin v-if="loading" style="display: flex; justify-content: center; margin-top: 80px" />
    <NEmpty v-else-if="resources.length === 0" description="暂无资源" />
    <div v-else style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px">
      <NCard v-for="r in resources" :key="r.id" hoverable size="small" @click="router.push(`/resources/${r.id}`)">
        <template #header>
          <div style="display: flex; justify-content: space-between; align-items: center">
            <NTag size="tiny">{{ typeLabels[r.resourceType] || r.resourceType }}</NTag>
            <NTag :type="(diffColors[r.difficulty] as never) || 'default'" size="tiny">{{ r.difficulty }}</NTag>
          </div>
        </template>
        <p style="margin: 0; font-size: 14px; font-weight: 500">{{ r.title }}</p>
        <p style="font-size: 12px; color: #999; margin: 4px 0 0">{{ new Date(r.createdAt).toLocaleDateString('zh-CN') }}</p>
      </NCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NCard, NSpin, NTag, NSpace, NStatistic, NGrid, NGi, NInput } from 'naive-ui'
import { knowledgeApi } from '@/api/client'

const loading = ref(true)
const stats = ref<{ node_count: number; edge_count: number; is_dag: boolean }>({ node_count: 0, edge_count: 0, is_dag: true })
const hubNodes = ref<{ topicCode: string; title: string; difficulty: string; pagerankScore?: number }[]>([])
const nodes = ref<{ id: string; topicCode: string; title: string; difficulty: string; depth: number }[]>([])
const searchQuery = ref('')
const searchResults = ref<{ id: string; topicCode: string; title: string; contentSnippet: string; similarity: number }[]>([])

const diffColors: Record<string, string> = { beginner: 'success', intermediate: 'warning', advanced: 'error' }

onMounted(async () => {
  loading.value = true
  try {
    const [graphRes, treeRes] = await Promise.all([
      knowledgeApi.getGraph(),
      knowledgeApi.getTree(),
    ])
    const graphData = graphRes.data
    const s = graphData.stats as Record<string, unknown> || {}
    stats.value = { node_count: Number(s.node_count || 0), edge_count: Number(s.edge_count || 0), is_dag: Boolean(s.is_dag) }
    // Show nodes grouped by depth
    nodes.value = (graphData.nodes as { id: string; topicCode: string; title: string; difficulty: string; depth: number }[]) || []
    // Compute hub nodes from the graph data
    hubNodes.value = (graphData.nodes as { id: string; topicCode: string; title: string; difficulty: string; pagerankScore?: number }[])
      ?.filter((n: { difficulty: string }) => n.difficulty === 'beginner')
      .slice(0, 10) || []
  } catch { /* graph may not be indexed yet */ }
  finally { loading.value = false }
})

async function doSearch() {
  if (!searchQuery.value.trim()) { searchResults.value = []; return }
  try {
    const res = await knowledgeApi.search(searchQuery.value, 8)
    searchResults.value = (res.data as { results: { id: string; topicCode: string; title: string; contentSnippet: string; similarity: number }[] }).results || []
  } catch { searchResults.value = [] }
}
</script>

<template>
  <div style="padding: 24px; height: calc(100vh - 80px); overflow-y: auto">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px">
      <h2 style="margin: 0">JavaScript 知识图谱</h2>
    </div>

    <NSpin v-if="loading" style="display: flex; justify-content: center; margin-top: 80px" />

    <template v-else>
      <!-- Stats -->
      <NGrid :cols="4" :x-gap="16" style="margin-bottom: 24px">
        <NGi><NCard size="small"><NStatistic label="知识点" :value="stats.node_count || 0" /></NCard></NGi>
        <NGi><NCard size="small"><NStatistic label="关联关系" :value="stats.edge_count || 0" /></NCard></NGi>
        <NGi><NCard size="small" style="display:flex;align-items:center;justify-content:center"><span style="font-size:14px;color:#666">DAG: <strong>{{ stats.is_dag ? '是' : '否' }}</strong></span></NCard></NGi>
        <NGi><NCard size="small"><NStatistic label="章节" value="10" /></NCard></NGi>
      </NGrid>

      <!-- Search -->
      <NCard size="small" title="搜索知识点" style="margin-bottom: 16px">
        <NSpace>
          <NInput v-model:value="searchQuery" placeholder="搜索 JavaScript 知识点..." size="large" style="width: 360px" @keyup.enter="doSearch" clearable />
        </NSpace>
        <div v-if="searchResults.length" style="margin-top: 12px">
          <div v-for="r in searchResults" :key="r.id" style="padding: 8px 0; border-bottom: 1px solid #f0f0f0">
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span style="font-weight: 500">{{ r.title }}</span>
              <NTag size="tiny">{{ (r.similarity * 100).toFixed(0) }}%</NTag>
            </div>
            <p style="font-size: 12px; color: #999; margin: 4px 0 0">{{ r.contentSnippet }}</p>
          </div>
        </div>
      </NCard>

      <!-- All nodes by depth -->
      <NCard size="small" title="知识点列表">
        <div v-for="depth in [1,2,3,4,5,6,7,8,9,10]" :key="depth">
          <template v-if="nodes.filter(n => n.depth === depth).length">
            <h4 style="margin: 12px 0 8px; color: #666">第{{ depth }}章</h4>
            <NSpace wrap>
              <NTag
                v-for="n in nodes.filter(n => n.depth === depth)"
                :key="n.id"
                :type="(diffColors[n.difficulty] as never) || 'default'"
                size="small"
              >
                {{ n.title }}
              </NTag>
            </NSpace>
          </template>
        </div>
      </NCard>
    </template>
  </div>
</template>

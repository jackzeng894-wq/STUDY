<script setup lang="ts">
import { NTag, NSpin } from 'naive-ui'
import type { AgentStatus } from '@/types'

defineProps<{
  agents: AgentStatus[]
}>()

const statusColors: Record<string, string> = {
  thinking: 'info',
  generating: 'success',
  reviewing: 'warning',
  done: 'default',
}

const statusLabels: Record<string, string> = {
  thinking: '思考中',
  generating: '生成中',
  reviewing: '审核中',
  done: '完成',
}
</script>

<template>
  <div v-if="agents.length > 0" class="agent-indicator">
    <NTag
      v-for="agent in agents"
      :key="agent.name"
      :type="(statusColors[agent.status] as never) || 'default'"
      size="small"
      round
    >
      <NSpin v-if="agent.status !== 'done'" size="small" />
      {{ agent.name }}
      <span class="status-label">{{ statusLabels[agent.status] || agent.status }}</span>
    </NTag>
  </div>
</template>

<style scoped>
.agent-indicator {
  display: flex;
  gap: 8px;
  padding: 8px 16px;
  flex-wrap: wrap;
  background: #fafafa;
  border-bottom: 1px solid #e8e8e8;
}

.status-label {
  margin-left: 4px;
  opacity: 0.7;
  font-size: 0.85em;
}
</style>

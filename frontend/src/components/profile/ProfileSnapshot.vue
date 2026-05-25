<script setup lang="ts">
import { computed } from 'vue'
import { NCard, NTag, NSpace, NEmpty } from 'naive-ui'
import type { StudentProfile, ProfileDiff } from '@/types'

const props = defineProps<{
  profile?: StudentProfile | null
  dimensions?: ProfileDiff[]
}>()

const topStrengths = computed(() => {
  if (!props.profile?.knowledgeFoundation) return []
  return Object.entries(props.profile.knowledgeFoundation)
    .filter(([, level]) => level === 'advanced' || level === 'expert')
    .slice(0, 3)
    .map(([topic]) => topic)
})

const topErrors = computed(() => {
  if (!props.profile?.commonErrors) return []
  return [...props.profile.commonErrors]
    .sort((a, b) => b.frequency - a.frequency)
    .slice(0, 3)
})

const hasProfile = computed(() =>
  props.profile && props.profile.profileConfidence > 0,
)

const hasUpdates = computed(() =>
  (props.dimensions || []).length > 0,
)

const dimLabels: Record<string, string> = {
  knowledge_foundation: '知识基础',
  cognitive_style: '认知风格',
  common_errors: '常见错误',
  learning_preferences: '学习偏好',
  learning_goals: '学习目标',
  time_commitment: '时间投入',
}
</script>

<template>
  <NCard title="学习画像" size="small">
    <!-- In-conversation profile updates -->
    <div v-if="hasUpdates" class="updates-section">
      <div v-for="d in dimensions" :key="d.dimension" class="update-row">
        <NTag size="tiny" type="info">{{ dimLabels[d.dimension] || d.dimension }}</NTag>
        <span class="update-arrow">已更新</span>
      </div>
    </div>

    <!-- Full profile snapshot -->
    <div v-if="hasProfile" class="snapshot-content">
      <div class="dim-row">
        <span class="label">认知风格</span>
        <NTag type="info" size="small">{{ profile?.cognitiveStyle }}</NTag>
      </div>
      <div class="dim-row">
        <span class="label">学习节奏</span>
        <NTag type="success" size="small">{{ profile?.learningPreferences?.pace || '-' }}</NTag>
      </div>
      <div class="dim-row">
        <span class="label">时间投入</span>
        <NTag type="warning" size="small">{{ profile?.timeCommitment }}</NTag>
      </div>
      <div v-if="topStrengths.length" class="dim-row">
        <span class="label">强项</span>
        <NSpace size="small" wrap>
          <NTag v-for="t in topStrengths" :key="t" size="tiny" round>{{ t }}</NTag>
        </NSpace>
      </div>
      <div v-if="topErrors.length" class="dim-row">
        <span class="label">常见错误</span>
        <NSpace size="small" wrap>
          <NTag v-for="e in topErrors" :key="e.pattern" size="tiny" type="error" round>
            {{ e.pattern }}
          </NTag>
        </NSpace>
      </div>
    </div>

    <NEmpty
      v-if="!hasProfile && !hasUpdates"
      description="暂无画像数据"
      size="small"
    />
  </NCard>
</template>

<style scoped>
.snapshot-content {
  font-size: 13px;
}

.dim-row {
  margin-bottom: 8px;
}

.label {
  font-size: 12px;
  color: #888;
  margin-right: 8px;
}

.updates-section {
  margin-bottom: 8px;
}

.update-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.update-arrow {
  font-size: 12px;
  color: #999;
}
</style>

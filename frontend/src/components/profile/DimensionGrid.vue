<script setup lang="ts">
import { NCard, NGrid, NGi, NTag, NSpace, NProgress } from 'naive-ui'
import type { StudentProfile } from '@/types'

const props = defineProps<{
  profile: StudentProfile
}>()

const knowledgeEntries = computed(() => {
  if (!props.profile.knowledgeFoundation) return []
  return Object.entries(props.profile.knowledgeFoundation).slice(0, 10)
})

const errorTopics = computed(() => {
  return (props.profile.commonErrors || []).slice(0, 8)
})

const goals = computed(() => {
  return (props.profile.learningGoals || []).slice(0, 5)
})

const paceLabel: Record<string, string> = { slow: '慢速', moderate: '适中', fast: '快速' }
const timeLabel: Record<string, string> = { minimal: '很少', moderate: '适中', substantial: '较多', intensive: '密集' }
</script>

<script lang="ts">
import { computed } from 'vue'
</script>

<template>
  <NGrid :cols="2" :x-gap="16" :y-gap="16">
    <!-- 知识基础 -->
    <NGi>
      <NCard title="知识基础" size="small">
        <div v-if="knowledgeEntries.length === 0" class="empty-dim">待评估</div>
        <div v-for="[topic, level] in knowledgeEntries" :key="topic" class="knowledge-row">
          <span class="topic-name">{{ topic }}</span>
          <NProgress
            :percentage="level === 'expert' ? 100 : level === 'advanced' ? 75 : level === 'intermediate' ? 50 : 25"
            :height="8"
            :color="level === 'expert' ? '#18a058' : level === 'advanced' ? '#2080f0' : level === 'intermediate' ? '#f0a020' : '#d03050'"
            :border-radius="4"
          />
          <NTag size="tiny">{{ level }}</NTag>
        </div>
      </NCard>
    </NGi>

    <!-- 认知风格 -->
    <NGi>
      <NCard title="认知风格" size="small">
        <div class="center-big">
          <NTag size="large" type="info" round>{{ profile.cognitiveStyle || 'unknown' }}</NTag>
        </div>
      </NCard>
    </NGi>

    <!-- 常见错误 -->
    <NGi>
      <NCard title="常见错误模式" size="small">
        <div v-if="errorTopics.length === 0" class="empty-dim">待评估</div>
        <NSpace v-else wrap>
          <NTag v-for="e in errorTopics" :key="e.pattern" type="error" size="small">
            {{ e.pattern }} ({{ e.frequency }}次)
          </NTag>
        </NSpace>
      </NCard>
    </NGi>

    <!-- 学习偏好 -->
    <NGi>
      <NCard title="学习偏好" size="small">
        <div class="dim-row">
          <span class="label">资源类型：</span>
          <NSpace v-if="profile.learningPreferences?.resourceTypes?.length" size="small" wrap>
            <NTag v-for="rt in profile.learningPreferences.resourceTypes" :key="rt" size="small">{{ rt }}</NTag>
          </NSpace>
          <span v-else class="empty-dim">待评估</span>
        </div>
        <div class="dim-row" style="margin-top: 12px">
          <span class="label">学习节奏：</span>
          <NTag type="success" size="small">
            {{ paceLabel[profile.learningPreferences?.pace] || profile.learningPreferences?.pace || '未知' }}
          </NTag>
        </div>
      </NCard>
    </NGi>

    <!-- 学习目标 -->
    <NGi>
      <NCard title="学习目标" size="small">
        <div v-if="goals.length === 0" class="empty-dim">待评估</div>
        <div v-for="g in goals" :key="g.goal" class="goal-row">
          <span>{{ g.goal }}</span>
          <NTag :type="g.priority === 'high' ? 'error' : g.priority === 'medium' ? 'warning' : 'default'" size="tiny">
            {{ g.priority }}
          </NTag>
        </div>
      </NCard>
    </NGi>

    <!-- 时间投入 -->
    <NGi>
      <NCard title="时间投入" size="small">
        <div class="center-big">
          <NTag size="large" type="warning" round>
            {{ timeLabel[profile.timeCommitment] || profile.timeCommitment }}
          </NTag>
        </div>
        <div style="text-align: center; margin-top: 8px; color: #999; font-size: 13px">
          置信度：{{ (profile.profileConfidence * 100).toFixed(0) }}% | 版本：v{{ profile.version }}
        </div>
      </NCard>
    </NGi>
  </NGrid>
</template>

<style scoped>
.empty-dim {
  color: #bbb;
  font-style: italic;
}
.dim-row {
  display: flex;
  align-items: center;
}
.label {
  font-size: 13px;
  color: #666;
  margin-right: 8px;
}
.center-big {
  text-align: center;
  padding: 20px;
}
.knowledge-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.topic-name {
  min-width: 100px;
  font-size: 12px;
  color: #666;
}
.knowledge-row :deep(.n-progress) {
  flex: 1;
}
.goal-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  font-size: 13px;
}
</style>

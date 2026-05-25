<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  NButton,
  NCard,
  NEmpty,
  NModal,
  NInput,
  NSelect,
  NSpin,
  NSpace,
  NTag,
  NPopconfirm,
} from 'naive-ui'
import { conversationApi } from '@/api/client'
import type { Conversation, ConversationType } from '@/types'

const router = useRouter()
const conversations = ref<Conversation[]>([])
const loading = ref(true)
const showCreate = ref(false)

const newTitle = ref('')
const newType = ref<ConversationType>('tutoring')

const typeOptions = [
  { label: '学习辅导', value: 'tutoring' },
  { label: '画像评估', value: 'profile_building' },
]

const typeLabels: Record<string, string> = {
  profile_building: '画像评估',
  tutoring: '学习辅导',
  resource_request: '资源生成',
  path_planning: '路径规划',
}

const typeColors: Record<string, string> = {
  profile_building: 'info',
  tutoring: 'success',
  resource_request: 'warning',
  path_planning: 'error',
}

onMounted(async () => {
  await loadConversations()
})

async function loadConversations() {
  loading.value = true
  try {
    const res = await conversationApi.list()
    conversations.value = res.data || []
  } catch {
    conversations.value = []
  } finally {
    loading.value = false
  }
}

async function createConversation() {
  if (!newTitle.value.trim()) return
  try {
    const res = await conversationApi.create(newType.value, newTitle.value)
    showCreate.value = false
    newTitle.value = ''
    router.push(`/conversations/${res.data.id}`)
  } catch {
    // Error handled by axios interceptor
  }
}

function openConversation(id: string) {
  router.push(`/conversations/${id}`)
}

async function deleteConversation(id: string) {
  try {
    await conversationApi.delete(id)
    conversations.value = conversations.value.filter((c) => c.id !== id)
  } catch {
    // handled
  }
}

function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 86400000) return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`
  return d.toLocaleDateString('zh-CN')
}
</script>

<template>
  <div class="conv-list-page">
    <div class="header">
      <h2>对话</h2>
      <NButton type="primary" @click="showCreate = true">新建对话</NButton>
    </div>

    <NSpin v-if="loading" class="loading" />

    <NEmpty v-else-if="conversations.length === 0" description="还没有对话记录，点击上方「新建对话」开始">
      <template #extra>
        <NButton type="primary" @click="showCreate = true">新建对话</NButton>
      </template>
    </NEmpty>

    <div v-else class="card-grid">
      <NCard
        v-for="conv in conversations"
        :key="conv.id"
        hoverable
        class="conv-card"
        @click="openConversation(conv.id)"
      >
        <template #header>
          <div class="card-header">
            <span class="card-title">{{ conv.title || '未命名对话' }}</span>
            <NSpace align="center" :wrap="false">
              <NTag :type="(typeColors[conv.conversationType] as never) || 'default'" size="small">
                {{ typeLabels[conv.conversationType] || conv.conversationType }}
              </NTag>
              <NPopconfirm @positive-click="deleteConversation(conv.id)">
                <template #trigger>
                  <NButton text size="tiny" type="error" @click.stop>删除</NButton>
                </template>
                确定删除这个对话吗？
              </NPopconfirm>
            </NSpace>
          </div>
        </template>
        <div class="card-meta">
          {{ conv.messages?.length || 0 }} 条消息 ·
          {{ formatDate(conv.createdAt) }}
        </div>
      </NCard>
    </div>

    <!-- Create modal -->
    <NModal v-model:show="showCreate" title="新建对话" preset="card" style="width: 420px">
      <NSpace vertical>
        <NSelect
          v-model:value="newType"
          :options="typeOptions"
          placeholder="对话类型"
          size="large"
        />
        <NInput
          v-model:value="newTitle"
          placeholder="对话标题（例如：JS闭包问题）"
          size="large"
          @keyup.enter="createConversation"
        />
        <NButton type="primary" block size="large" @click="createConversation">
          开始对话
        </NButton>
      </NSpace>
    </NModal>
  </div>
</template>

<style scoped>
.conv-list-page {
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

.card-grid {
  display: grid;
  gap: 12px;
}

.conv-card {
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.conv-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.card-title {
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-meta {
  font-size: 13px;
  color: #999;
}
</style>

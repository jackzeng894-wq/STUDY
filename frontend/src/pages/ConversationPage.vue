<script setup lang="ts">
/** Core conversation page: chat panel + agent status bar + context sidebar.
 *
 * Supports 3 conversation types:
 *  - profile_building: AI interviews student to build learning profile
 *  - tutoring: Real-time JavaScript Q&A tutoring
 *  - resource_request: Resource generation (redirects to resource flow)
 */
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useConversationStore } from '@/stores/conversation'
import { conversationApi } from '@/api/client'
import { useSSE } from '@/composables/useSSE'
import MessageList from '@/components/chat/MessageList.vue'
import MessageInput from '@/components/chat/MessageInput.vue'
import AgentThinkingIndicator from '@/components/chat/AgentThinkingIndicator.vue'
import ProfileSnapshot from '@/components/profile/ProfileSnapshot.vue'
import type { ConversationType } from '@/types'

const route = useRoute()
const router = useRouter()
const store = useConversationStore()
const { isConnected, connect, disconnect } = useSSE()

const conversationId = ref(route.params.id as string)
const inputText = ref('')
const loading = ref(false)
const conversationTitle = ref('')
const conversationType = ref<ConversationType>('tutoring')

onMounted(() => {
  store.reset()
  if (conversationId.value) {
    loadConversation()
  }
})

// Watch for route param changes (switching conversations)
watch(
  () => route.params.id,
  (newId) => {
    if (newId && newId !== conversationId.value) {
      store.reset()
      conversationId.value = newId as string
      loadConversation()
    }
  },
)

onUnmounted(() => {
  disconnect()
  store.reset()
})

async function loadConversation() {
  loading.value = true
  try {
    const res = await conversationApi.get(conversationId.value)
    store.messages = (res.data.messages || []).map((m) => ({
      ...m,
      role: m.role as 'user' | 'assistant' | 'system',
      conversationId: m.conversationId || conversationId.value,
    }))
    conversationType.value = res.data.conversationType as ConversationType
    conversationTitle.value = res.data.title || ''
  } catch {
    store.addMessage({
      id: crypto.randomUUID(),
      conversationId: conversationId.value,
      role: 'system',
      content: '加载对话失败，请返回重试',
      metadata: {},
      createdAt: new Date().toISOString(),
    })
  } finally {
    loading.value = false
  }
}

async function sendMessage() {
  const content = inputText.value.trim()
  if (!content || store.isStreaming || !conversationId.value) return

  inputText.value = ''

  // Add user message optimistically
  store.addMessage({
    id: crypto.randomUUID(),
    conversationId: conversationId.value,
    role: 'user',
    content,
    metadata: {},
    createdAt: new Date().toISOString(),
  })

  store.isStreaming = true

  try {
    // Send to backend (agent starts processing)
    await conversationApi.sendMessage(conversationId.value, content)
  } catch {
    store.isStreaming = false
    store.addMessage({
      id: crypto.randomUUID(),
      conversationId: conversationId.value,
      role: 'system',
      content: '消息发送失败，请检查网络后重试',
      metadata: {},
      createdAt: new Date().toISOString(),
    })
    return
  }

  // Connect SSE to receive agent output
  // The backend processes in background and pushes events
  connect(conversationApi.streamUrl(conversationId.value))
}

function newConversation() {
  store.reset()
  router.push('/conversations')
}

const typeLabels: Record<string, string> = {
  profile_building: '画像评估',
  tutoring: '学习辅导',
  resource_request: '资源生成',
}
</script>

<template>
  <div class="conversation-page">
    <!-- Header -->
    <div class="conv-header">
      <div class="conv-info">
        <h3>{{ conversationTitle || '对话' }}</h3>
        <span class="conv-type">{{ typeLabels[conversationType] || conversationType }}</span>
      </div>
    </div>

    <!-- Agent status bar -->
    <AgentThinkingIndicator :agents="store.activeAgentList" />

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <p>加载对话中...</p>
    </div>

    <!-- Empty state for new conversations -->
    <div v-else-if="store.messages.length === 0" class="empty-state">
      <div class="empty-icon">&#128172;</div>
      <h3 v-if="conversationType === 'profile_building'">开始画像评估</h3>
      <h3 v-else-if="conversationType === 'tutoring'">JavaScript 学习助手</h3>
      <h3 v-else>开始对话</h3>
      <p v-if="conversationType === 'profile_building'">
        AI 将逐步了解你的 JavaScript 水平，请自然回答问题即可
      </p>
      <p v-else-if="conversationType === 'tutoring'">
        随时提出 JavaScript 相关问题，AI 导师将基于知识库为你解答
      </p>
      <p v-else>输入你的需求，AI 智能体将为你生成个性化学习资源</p>
    </div>

    <!-- Chat area -->
    <MessageList
      v-else
      :messages="store.messages"
      :is-streaming="store.isStreaming"
    />

    <!-- Profile context (shown during profile_building) -->
    <div v-if="conversationType === 'profile_building' && store.profileUpdates.length > 0" class="profile-context">
      <ProfileSnapshot :dimensions="store.profileUpdates" />
    </div>

    <!-- Input area -->
    <MessageInput
      v-model="inputText"
      :disabled="store.isStreaming"
      :placeholder="
        conversationType === 'profile_building'
          ? '回答面试官的问题...'
          : '输入 JavaScript 相关问题...'
      "
      @send="sendMessage"
    />
  </div>
</template>

<style scoped>
.conversation-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 60px);
  background: #fff;
}

.conv-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  border-bottom: 1px solid #e8e8e8;
}

.conv-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.conv-info h3 {
  margin: 0;
}

.conv-type {
  font-size: 12px;
  color: #666;
  background: #f0f0f0;
  padding: 2px 8px;
  border-radius: 4px;
}

.loading-state,
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #999;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.empty-state h3 {
  margin: 0 0 8px;
  color: #333;
}

.empty-state p {
  max-width: 360px;
  text-align: center;
  line-height: 1.6;
}

.profile-context {
  padding: 8px 16px;
  background: #f0f7ff;
  border-top: 1px solid #d6e4ff;
}
</style>

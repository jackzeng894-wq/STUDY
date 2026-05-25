<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import type { Message } from '@/types'
import MarkdownRenderer from './MarkdownRenderer.vue'

const props = defineProps<{
  messages: Message[]
  isStreaming?: boolean
}>()

const listRef = ref<HTMLElement | null>(null)

function scrollToBottom() {
  nextTick(() => {
    if (listRef.value) {
      listRef.value.scrollTop = listRef.value.scrollHeight
    }
  })
}

watch(
  () => props.messages.length,
  () => scrollToBottom()
)

watch(
  () => props.messages[props.messages.length - 1]?.content,
  () => { if (props.isStreaming) scrollToBottom() }
)
</script>

<template>
  <div ref="listRef" class="message-list">
    <div v-if="messages.length === 0" class="empty-hint">
      输入问题开始与 AI 智能体对话
    </div>
    <div
      v-for="msg in messages"
      :key="msg.id"
      class="message-wrapper"
      :class="msg.role"
    >
      <div class="message-bubble">
        <div class="message-role">{{ msg.role === 'user' ? '我' : msg.role === 'system' ? '系统' : 'AI 智能体' }}</div>
        <MarkdownRenderer
          v-if="msg.role === 'assistant'"
          :content="msg.content"
          :is-streaming="isStreaming && msg === messages[messages.length - 1]"
        />
        <p v-else class="message-text">{{ msg.content }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.empty-hint {
  text-align: center;
  color: #999;
  margin-top: 30%;
  font-size: 15px;
}

.message-wrapper {
  display: flex;
  margin-bottom: 16px;
}

.message-wrapper.user {
  justify-content: flex-end;
}

.message-wrapper.assistant,
.message-wrapper.system {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 75%;
  padding: 12px 16px;
  border-radius: 12px;
}

.message-wrapper.user .message-bubble {
  background: #1890ff;
  color: #fff;
}

.message-wrapper.assistant .message-bubble {
  background: #f5f5f5;
  border: 1px solid #e8e8e8;
}

.message-wrapper.system .message-bubble {
  background: #fff7e6;
  border: 1px solid #ffd591;
}

.message-role {
  font-size: 12px;
  opacity: 0.7;
  margin-bottom: 4px;
}

.message-text {
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}
</style>

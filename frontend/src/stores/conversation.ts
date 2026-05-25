/** Event-driven Pinia store for conversation state management.

SSE events dispatch to this store; components react to store changes.
Components never listen to SSE directly.
*/

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Message, AgentStatus, ResourcePreview, ProfileDiff } from '@/types'

export const useConversationStore = defineStore('conversation', () => {
  // ---- State ----

  const messages = ref<Message[]>([])
  const activeAgents = ref<Map<string, AgentStatus>>(new Map())
  const pendingResources = ref<ResourcePreview[]>([])
  const approvedResources = ref<ResourcePreview[]>([])
  const profileUpdates = ref<ProfileDiff[]>([])
  const isStreaming = ref(false)

  // ---- Getters ----

  const lastAssistantMessage = computed(() =>
    messages.value.filter((m) => m.role === 'assistant').pop() || null
  )

  const activeAgentList = computed(() =>
    Array.from(activeAgents.value.values())
  )

  const hasPendingResources = computed(() =>
    pendingResources.value.length > 0
  )

  // ---- Actions ----

  function addMessage(msg: Message) {
    messages.value.push(msg)
  }

  /** Append a token to the last assistant message (for streaming). */
  function appendToken(content: string) {
    const last = lastAssistantMessage.value
    if (last && last.role === 'assistant') {
      last.content += content
    } else {
      // First token: create a new assistant message
      const newMsg: Message = {
        id: crypto.randomUUID(),
        conversationId: '',
        role: 'assistant',
        content,
        metadata: {},
        createdAt: new Date().toISOString(),
      }
      messages.value.push(newMsg)
    }
  }

  function updateAgentStatus(name: string, status: AgentStatus) {
    activeAgents.value.set(name, status)
    // Force reactivity
    activeAgents.value = new Map(activeAgents.value)
  }

  function removeAgent(name: string) {
    activeAgents.value.delete(name)
    activeAgents.value = new Map(activeAgents.value)
  }

  function addPendingResource(resource: ResourcePreview) {
    pendingResources.value.push(resource)
  }

  function approveResource(resourceId: string) {
    const idx = pendingResources.value.findIndex((r) => r.resourceId === resourceId)
    if (idx >= 0) {
      const [resource] = pendingResources.value.splice(idx, 1)
      approvedResources.value.push(resource)
    }
  }

  function addProfileUpdate(diff: ProfileDiff) {
    profileUpdates.value.push(diff)
  }

  function reset() {
    messages.value = []
    activeAgents.value = new Map()
    pendingResources.value = []
    approvedResources.value = []
    profileUpdates.value = []
    isStreaming.value = false
  }

  return {
    messages,
    activeAgents,
    pendingResources,
    approvedResources,
    profileUpdates,
    isStreaming,
    lastAssistantMessage,
    activeAgentList,
    hasPendingResources,
    addMessage,
    appendToken,
    updateAgentStatus,
    removeAgent,
    addPendingResource,
    approveResource,
    addProfileUpdate,
    reset,
  }
})

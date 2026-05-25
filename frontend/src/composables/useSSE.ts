/** SSE (Server-Sent Events) composable for real-time agent streaming.

Dispatches parsed SSE events to the Pinia store. Components never
listen to EventSource directly -- they observe the store instead,
making it trivial to test or swap to WebSocket later.
*/

import { ref, onUnmounted } from 'vue'
import { useConversationStore } from '@/stores/conversation'
import type { SSEEvent } from '@/types'

export function useSSE() {
  const isConnected = ref(false)
  const error = ref<string | null>(null)
  let eventSource: EventSource | null = null

  function connect(url: string) {
    const store = useConversationStore()

    // Close existing connection
    disconnect()

    eventSource = new EventSource(url)
    isConnected.value = true
    error.value = null

    eventSource.addEventListener('token', (e: MessageEvent) => {
      const data: SSEEvent = JSON.parse(e.data)
      store.appendToken(data.data.content as string)
    })

    eventSource.addEventListener('agent_step', (e: MessageEvent) => {
      const data: SSEEvent = JSON.parse(e.data)
      const agentData = data.data as { name: string; role: string; status: 'thinking' | 'generating' | 'reviewing' | 'done'; progress: number }
      store.updateAgentStatus(agentData.name, {
        name: agentData.name,
        role: agentData.role,
        status: agentData.status,
        progress: agentData.progress,
      })
    })

    eventSource.addEventListener('resource_ready', (e: MessageEvent) => {
      const data: SSEEvent = JSON.parse(e.data)
      store.approveResource(data.data.resourceId as string)
    })

    eventSource.addEventListener('profile_update', (e: MessageEvent) => {
      const data: SSEEvent = JSON.parse(e.data)
      store.addProfileUpdate(data.data as never)
    })

    eventSource.addEventListener('done', () => {
      store.isStreaming = false
      store.activeAgents = new Map()
      disconnect()
    })

    eventSource.addEventListener('error', (e: MessageEvent) => {
      if (e.data) {
        const data: SSEEvent = JSON.parse(e.data)
        error.value = (data.data.message as string) || 'Stream error'
      }
      store.isStreaming = false
      disconnect()
    })

    eventSource.onerror = () => {
      // EventSource auto-reconnects; only mark as error if closed
      if (eventSource?.readyState === EventSource.CLOSED) {
        isConnected.value = false
        store.isStreaming = false
      }
    }
  }

  function disconnect() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    isConnected.value = false
  }

  onUnmounted(() => {
    disconnect()
  })

  return { isConnected, error, connect, disconnect }
}

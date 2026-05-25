/** API client: centralized HTTP and SSE methods for the backend.
 *
 * All API calls go through here so the base URL, auth headers, and
 * error handling are configured once.
 */

import axios from 'axios'
import type { AxiosError } from 'axios'
import type {
  Conversation,
  ConversationType,
  KnowledgeNode,
  LearningPath,
  Resource,
  StudentProfile,
} from '@/types'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1'

const http = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

// ── JWT Token Management ──────────────────────────────────────────────

const TOKEN_KEY = 'auth_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export function isAuthenticated(): boolean {
  return !!getToken()
}

// Attach token to every request
http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 globally
http.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      clearToken()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

// ── SSE URL builder ──────────────────────────────────────────────────

export function sseUrl(path: string): string {
  return `${API_BASE}${path}`
}

// ── Auth ─────────────────────────────────────────────────────────────

export interface AuthResponse {
  access_token: string
  token_type: string
}

export const authApi = {
  register: (data: { username: string; email?: string; password: string }) =>
    http.post<AuthResponse>('/auth/register', data),

  login: (data: { username: string; password: string }) =>
    http.post<AuthResponse>('/auth/login', data),

  getMe: () => http.get('/auth/me'),
}

// ── Conversations ─────────────────────────────────────────────────────

export const conversationApi = {
  list: () => http.get<Conversation[]>('/conversations'),

  create: (type: ConversationType, title?: string) =>
    http.post<Conversation>('/conversations', {
      conversation_type: type,
      title,
    }),

  get: (id: string) =>
    http.get<Conversation & { messages: Conversation['messages'] }>(
      `/conversations/${id}`,
    ),

  sendMessage: (conversationId: string, content: string) =>
    http.post(`/conversations/${conversationId}/messages`, { content }),

  streamUrl: (conversationId: string) =>
    sseUrl(`/conversations/${conversationId}/stream`),

  delete: (id: string) => http.delete(`/conversations/${id}`),
}

// ── Profiles ──────────────────────────────────────────────────────────

export const profileApi = {
  get: () => http.get<StudentProfile>('/profiles'),
  getDimensions: () => http.get<{ dimension: string; value: unknown }[]>('/profiles/dimensions'),
  refresh: () => http.post('/profiles/refresh'),
}

// ── Resources ─────────────────────────────────────────────────────────

export const resourceApi = {
  list: (params?: Record<string, string>) =>
    http.get<{ items: Resource[]; total: number }>('/resources', { params }),

  generate: (data: { topic_codes: string[]; resource_types?: string[]; constraints?: string }) =>
    http.post<{ message: string; conversation_id: string; task_count: number }>(
      '/resources/generate',
      data,
    ),

  generateStreamUrl: (taskId: string) => sseUrl(`/resources/generate/${taskId}/stream`),

  get: (id: string) => http.get<Resource>(`/resources/${id}`),
}

// ── Learning Paths ────────────────────────────────────────────────────

export const pathApi = {
  list: () =>
    http.get<{ items: LearningPath[]; total: number }>('/learning-paths'),

  getActive: () => http.get<LearningPath>('/learning-paths/active'),

  generate: (data?: { learning_goal?: string; target_topic?: string }) =>
    http.post('/learning-paths/generate', data),

  get: (id: string) => http.get<LearningPath>(`/learning-paths/${id}`),

  updateNodeStatus: (pathId: string, nodeOrder: number, status: string) =>
    http.patch(`/learning-paths/${pathId}/nodes/${nodeOrder}`, { status }),

  replan: () => http.post('/learning-paths/replan'),
}

// ── Knowledge ─────────────────────────────────────────────────────────

export const knowledgeApi = {
  getTree: () => http.get<{ chapters: unknown[]; total_nodes: number }>('/knowledge/tree'),
  getGraph: () => http.get<{ nodes: unknown[]; edges: unknown[]; stats: unknown }>('/knowledge/graph'),
  search: (query: string, topK = 5) =>
    http.get('/knowledge/search', { params: { q: query, top_k: topK } }),
  listNodes: (params?: Record<string, string>) =>
    http.get<KnowledgeNode[]>('/knowledge/nodes', { params }),
  getNode: (id: string) => http.get<KnowledgeNode>(`/knowledge/nodes/${id}`),
}

// ── Evaluation ────────────────────────────────────────────────────────

export const evaluationApi = {
  assess: (focus = 'comprehensive', days = 30) =>
    http.post('/evaluation/assess', null, { params: { focus, days } }),

  getDashboard: () =>
    http.get<{
      profile_confidence: number
      active_path: { title: string; progress: number; total_nodes: number; completed_nodes: number } | null
      recent_activities_7d: number
      total_resources: number
      total_exercises: number
    }>('/evaluation/dashboard'),

  getLatestReport: () => http.get('/evaluation/report'),
}

export default http

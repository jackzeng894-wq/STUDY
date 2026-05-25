/** Core TypeScript type definitions shared across the frontend. */

// ---- Student ----
export interface Student {
  id: string
  username: string
  email: string | null
  avatarUrl: string | null
}

// ---- Profile (6 dimensions) ----
export interface StudentProfile {
  id: string
  studentId: string
  knowledgeFoundation: Record<string, string> // topic -> mastery level
  cognitiveStyle: 'visual' | 'auditory' | 'kinesthetic' | 'reading_writing' | 'mixed' | 'unknown'
  commonErrors: CommonError[]
  learningPreferences: LearningPreferences
  learningGoals: LearningGoal[]
  timeCommitment: 'minimal' | 'moderate' | 'substantial' | 'intensive'
  profileConfidence: number
  version: number
}

export interface CommonError {
  pattern: string
  topic: string
  frequency: number
}

export interface LearningPreferences {
  resourceTypes: string[]
  pace: 'slow' | 'moderate' | 'fast'
}

export interface LearningGoal {
  goal: string
  priority: 'high' | 'medium' | 'low'
  targetDate: string | null
}

// ---- Conversation ----
export type ConversationType = 'profile_building' | 'resource_request' | 'path_planning' | 'tutoring'

export interface Conversation {
  id: string
  studentId: string
  conversationType: ConversationType
  title: string | null
  messages: Message[]
  createdAt: string
}

export interface Message {
  id: string
  conversationId: string
  role: 'user' | 'assistant' | 'system'
  content: string
  metadata: MessageMetadata
  createdAt: string
}

export interface MessageMetadata {
  profileUpdates?: ProfileDiff[]
  resourceCards?: ResourcePreview[]
  agentStatus?: AgentState
  enhancements?: Record<string, unknown>
  [key: string]: unknown
}

export interface ProfileDiff {
  dimension: string
  previousValue: unknown
  newValue: unknown
}

// ---- Agent State ----
export interface AgentState {
  activeAgents: Map<string, AgentStatus>
}

export interface AgentStatus {
  name: string
  role: string
  status: 'thinking' | 'generating' | 'reviewing' | 'done'
  progress: number // 0.0 - 1.0
}

// ---- Resources (8 types) ----
export type ResourceType =
  | 'design_plan'
  | 'course_doc'
  | 'mind_map'
  | 'exercise'
  | 'code_case'
  | 'ppt'
  | 'project'
  | 'reading'
  | 'video_script'

export interface Resource {
  id: string
  resourceType: ResourceType
  title: string
  content: Record<string, unknown> // Type-specific JSONB
  knowledgeNodeIds: string[]
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  targetStudentId: string | null
  reviewStatus: 'pending' | 'approved' | 'rejected' | 'needs_revision'
  createdAt: string
}

export interface ResourcePreview {
  resourceId: string
  resourceType: ResourceType
  title: string
  summary: string
}

// ---- Knowledge Graph ----
export interface KnowledgeNode {
  id: string
  topicCode: string
  title: string
  description: string | null
  parentId: string | null
  depth: number
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  prerequisites: string[]
  keywords: string[]
}

export interface KnowledgeRelation {
  id: string
  sourceNodeId: string
  targetNodeId: string
  relationType: 'prerequisite' | 'related' | 'extends' | 'contrasts'
  weight: number
}

export interface GraphData {
  nodes: KnowledgeNode[]
  relations: KnowledgeRelation[]
}

// ---- Learning Path ----
export interface LearningPath {
  id: string
  studentId: string
  title: string | null
  description: string | null
  pathNodes: PathNode[]
  totalNodes: number
  completedNodes: number
  estimatedTotalHours: number | null
  status: 'active' | 'completed' | 'paused' | 'superseded'
  version: number
  createdAt: string
  updatedAt: string
}

export interface PathNode {
  knowledgeNodeId: string
  order: number
  status: 'locked' | 'active' | 'completed' | 'skipped'
  recommendedResources: string[]
  estimatedMinutes: number
}

// ---- SSE Events ----
export type SSEEventType = 'token' | 'agent_step' | 'resource_ready' | 'profile_update' | 'done' | 'error'

export interface SSEEvent {
  event: SSEEventType
  data: Record<string, unknown>
}

export interface User {
  id: number
  email: string
  full_name: string
  role: string
  is_active: boolean
  created_at: string
}

export interface DocumentRecord {
  id: string
  file_name: string
  content_type: string
  size_bytes: number
  status: string
  error: string | null
  created_at: string
}

export interface Conversation {
  id: number
  title: string
  document_id?: string | null
  created_at: string
  updated_at: string
}

export interface RetrievalEvidence {
  document_id: string | null
  file_name?: string | null
  text: string
  score?: number | null
  retrieval_source?: string | null
}

export interface Message {
  id: number
  conversation_id: number
  role: 'user' | 'assistant'
  content: string
  confidence_score: number | null
  web_search_used: boolean
  sources: unknown[]
  trace: unknown[]
  retrieval_evidence: RetrievalEvidence[]
  created_at: string
}

export interface DocumentContent {
  document_id: string
  file_name: string
  text: string | null
}

export interface ChatModelInfo {
  generation_model: string
  embedding_model: string
  rerank_model: string
  grader_model: string
  provider: string
}

export interface IngestionModelInfo {
  extraction_model: string
  embedding_model: string
  provider: string
}

export interface ModelsInfo {
  chat: ChatModelInfo
  ingestion: IngestionModelInfo
}

export interface DependencyStatus {
  name: string
  status: string
  detail: string | null
}

export interface SystemStats {
  users: number
  documents: number
  ingestion_jobs: Record<string, number>
  conversations: number
  messages: number
  query_logs: number
  dependencies: DependencyStatus[]
}

export interface AdminDocument extends DocumentRecord {
  user_id: number
  owner_email: string
  owner_full_name: string
}

export interface AdminConversation {
  id: number
  title: string
  document_id: string | null
  user_id: number
  owner_email: string
  owner_full_name: string
  message_count: number
  created_at: string
  updated_at: string
}

export interface AdminMessage {
  id: number
  conversation_id: number
  conversation_title: string
  user_id: number
  owner_email: string
  role: 'user' | 'assistant'
  content: string
  confidence_score: number | null
  web_search_used: boolean
  created_at: string
}

export interface AdminQueryLog {
  id: number
  user_id: number
  owner_email: string
  query: string
  answer: string
  confidence_score: number
  web_search_used: boolean
  retry_count: number
  latency_ms: number
  created_at: string
}
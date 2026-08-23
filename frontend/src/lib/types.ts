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
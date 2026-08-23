"""Stable API and internal data contracts."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(default="", max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class CsrfResponse(BaseModel):
    csrf_token: str


class DocumentResponse(BaseModel):
    id: str
    file_name: str
    content_type: str
    size_bytes: int
    status: str
    error: str | None = None
    created_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]


class DocumentContentResponse(BaseModel):
    document_id: str
    file_name: str
    text: str | None = None


class ChatModelInfo(BaseModel):
    generation_model: str
    embedding_model: str
    rerank_model: str
    grader_model: str
    provider: str


class IngestionModelInfo(BaseModel):
    extraction_model: str
    embedding_model: str
    provider: str


class ModelsInfoResponse(BaseModel):
    chat: ChatModelInfo
    ingestion: IngestionModelInfo


class IngestionJobResponse(BaseModel):
    id: int
    document_id: str
    status: str
    parent_chunks: int
    child_chunks: int
    graph_relationships: int
    error: str | None = None
    created_at: datetime


class ConversationResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]


class CreateConversationRequest(BaseModel):
    title: str = Field(default="New conversation", max_length=255)


class UpdateConversationRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    confidence_score: float | None = None
    web_search_used: bool = False
    sources: list[Any] = Field(default_factory=list)
    trace: list[Any] = Field(default_factory=list)
    retrieval_evidence: list[Any] = Field(default_factory=list)
    created_at: datetime


class MessageListResponse(BaseModel):
    items: list[MessageResponse]


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class AdminUserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


class AdminUsersResponse(BaseModel):
    items: list[AdminUserResponse]


class AdminDocumentsResponse(BaseModel):
    items: list[DocumentResponse]


class AdminIngestionsResponse(BaseModel):
    items: list[IngestionJobResponse]


class HealthResponse(BaseModel):
    status: str = "ok"


class DependencyStatus(BaseModel):
    name: str
    status: str
    detail: str | None = None


class SystemStats(BaseModel):
    users: int
    documents: int
    ingestion_jobs: dict[str, int] = Field(default_factory=dict)
    conversations: int
    messages: int
    query_logs: int
    dependencies: list[DependencyStatus] = Field(default_factory=list)


class ReadinessResponse(BaseModel):
    status: str
    dependencies: list[DependencyStatus]


class DetailResponse(BaseModel):
    message: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=16, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class SupportMessageOut(BaseModel):
    id: int
    sender_role: str
    content: str
    created_at: datetime


class SupportThreadOut(BaseModel):
    id: int
    subject: str
    status: str
    user_email: str | None = None
    user_full_name: str | None = None
    messages: list[SupportMessageOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class SupportThreadListResponse(BaseModel):
    items: list[SupportThreadOut]


class CreateSupportThreadRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    message: str = Field(min_length=1, max_length=4000)


class SupportReplyRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class SupportStatusUpdateRequest(BaseModel):
    status: Literal["open", "pending", "resolved"]


class RecentConversationItem(BaseModel):
    id: int
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class AdminUserDetailResponse(BaseModel):
    profile: AdminUserResponse
    document_count: int
    conversation_count: int
    message_count: int
    query_log_count: int
    storage_bytes: int
    recent_documents: list[DocumentResponse] = Field(default_factory=list)
    recent_conversations: list[RecentConversationItem] = Field(default_factory=list)


class AdminUserStatusUpdateRequest(BaseModel):
    is_active: bool

"""Conversation workflow: run the agent and persist messages and query logs."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from langchain_core.documents import Document
from sqlalchemy.orm import Session

from src.agents.graph import run_agent
from src.db.models import Conversation, Message, QueryLog, User


def _build_retrieval_evidence(documents: list[Document]) -> list[dict[str, Any]]:
    """Capture the chunks that grounded an answer for later highlighting."""
    evidence: list[dict[str, Any]] = []
    seen: set[str] = set()
    for document in documents:
        text = (document.page_content or "").strip()
        if not text:
            continue
        metadata = document.metadata or {}
        document_id = str(metadata.get("document_id") or "") or None
        key = f"{document_id}:{hash(text)}"
        if key in seen:
            continue
        seen.add(key)
        evidence.append(
            {
                "document_id": document_id,
                "file_name": metadata.get("file_name") or metadata.get("source"),
                "text": text,
                "score": float(metadata["score"]) if "score" in metadata else None,
                "retrieval_source": metadata.get("retrieval_source"),
            }
        )
    return evidence


def run_conversation_turn(
    db: Session,
    conversation: Conversation,
    user: User,
    content: str,
) -> Message:
    """Persist the user message, run the agent, persist the assistant reply."""
    user_message = Message(
        conversation_id=conversation.id,
        user_id=user.id,
        role="user",
        content=content,
    )
    db.add(user_message)
    db.flush()

    started = time.perf_counter()
    state = run_agent(content)
    latency_ms = int((time.perf_counter() - started) * 1000)

    assistant_message = Message(
        conversation_id=conversation.id,
        user_id=user.id,
        role="assistant",
        content=state.get("generation", ""),
        confidence_score=state.get("confidence_score", 0.0),
        web_search_used=bool(state.get("web_search_used", False)),
        sources=list(state.get("sources", [])),
        trace=list(state.get("retrieval_trace", [])),
        retrieval_evidence=_build_retrieval_evidence(list(state.get("documents") or [])),
    )
    db.add(assistant_message)
    db.flush()

    db.add(
        QueryLog(
            user_id=user.id,
            query=content,
            answer=assistant_message.content,
            confidence_score=assistant_message.confidence_score or 0.0,
            web_search_used=assistant_message.web_search_used,
            retry_count=int(state.get("retry_count", 0)),
            latency_ms=latency_ms,
        )
    )

    conversation.updated_at = datetime.now(UTC)
    db.commit()
    return assistant_message

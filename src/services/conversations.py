"""Conversation workflow: run the agent and persist messages and query logs."""

from __future__ import annotations

import time
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

from langchain_core.documents import Document
from langchain_core.language_models.chat_models import BaseChatModel
from sqlalchemy.orm import Session

from src.agents.graph import run_agent
from src.agents.nodes import (
    NO_CONTEXT_MESSAGE,
    build_answer_prompt,
    generation_failed_answer,
    heuristic_answer,
)
from src.config import get_settings
from src.db.models import Conversation, Message, QueryLog, User
from src.exceptions import ConfigurationError
from src.pipeline.llm import build_chat_model


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
    state = run_agent(content, document_id=conversation.document_id)
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


def stream_conversation_turn(
    db: Session,
    conversation: Conversation,
    user: User,
    content: str,
    *,
    chat_model: BaseChatModel | None = None,
) -> Iterable[dict[str, Any]]:
    """Persist the user message, stream the assistant reply as SSE events.

    The agent workflow runs up to the generate node; answer tokens are then
    streamed from the chat model and persisted once generation completes.
    Yields ``{"type": "delta", "content": ...}`` events followed by a final
    ``{"type": "done", "message": <Message>}`` event, or an error event when
    the model is unavailable.
    """
    db.add(
        Message(
            conversation_id=conversation.id,
            user_id=user.id,
            role="user",
            content=content,
        )
    )
    db.commit()

    started = time.perf_counter()
    state = run_agent(content, document_id=conversation.document_id, capture_generation_only=True)
    latency_ms = int((time.perf_counter() - started) * 1000)

    trace = list(state.get("retrieval_trace") or [])
    documents = list(state.get("documents") or [])

    if not documents:
        yield {"type": "delta", "content": NO_CONTEXT_MESSAGE}
        message = _build_assistant_message(
            conversation, user, NO_CONTEXT_MESSAGE, state, latency_ms, trace
        )
        db.add(message)
        db.flush()
        db.add(_query_log(user, content, message, state, latency_ms))
        _touch(conversation)
        db.commit()
        yield {"type": "done", "message": message}
        return

    active_model = chat_model
    if active_model is None:
        try:
            active_model = build_chat_model(
                get_settings(),
                num_ctx=get_settings().generation_num_ctx,
                num_predict=get_settings().max_output_tokens,
            )
        except ConfigurationError:
            text = heuristic_answer(content, documents)
            yield {"type": "delta", "content": text}
            message = _build_assistant_message(
                conversation, user, text, state, latency_ms, trace
            )
            db.add(message)
            db.flush()
            db.add(_query_log(user, content, message, state, latency_ms))
            _touch(conversation)
            db.commit()
            yield {"type": "done", "message": message}
            return

    chunks: list[str] = []
    try:
        for chunk in active_model.stream(
            build_answer_prompt(content, documents, get_settings())
        ):
            token = _chunk_text(chunk)
            if not token:
                continue
            chunks.append(token)
            yield {"type": "delta", "content": token}
    except Exception:
        trace.append("generate: stream failed")
        yield {
            "type": "error",
            "detail": "Generation stopped unexpectedly; partial answer saved.",
        }

    answer = "".join(chunks)
    if not answer:
        answer = generation_failed_answer(documents)
        yield {"type": "delta", "content": answer}

    message = _build_assistant_message(
        conversation, user, answer, state, latency_ms, trace
    )
    db.add(message)
    db.flush()
    db.add(_query_log(user, content, message, state, latency_ms))
    _touch(conversation)
    db.commit()
    yield {"type": "done", "message": message}


def _chunk_text(chunk: Any) -> str:
    content = getattr(chunk, "content", chunk)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(str(text))
        return "".join(parts)
    return str(content)


def _build_assistant_message(
    conversation: Conversation,
    user: User,
    content: str,
    state: dict[str, Any],
    latency_ms: int,
    trace: list[Any],
) -> Message:
    del latency_ms
    return Message(
        conversation_id=conversation.id,
        user_id=user.id,
        role="assistant",
        content=content,
        confidence_score=state.get("confidence_score", 0.0),
        web_search_used=bool(state.get("web_search_used", False)),
        sources=list(state.get("sources", [])),
        trace=trace,
        retrieval_evidence=_build_retrieval_evidence(list(state.get("documents") or [])),
    )


def _query_log(
    user: User,
    query: str,
    message: Message,
    state: dict[str, Any],
    latency_ms: int,
) -> QueryLog:
    return QueryLog(
        user_id=user.id,
        query=query,
        answer=message.content,
        confidence_score=message.confidence_score or 0.0,
        web_search_used=message.web_search_used,
        retry_count=int(state.get("retry_count", 0)),
        latency_ms=latency_ms,
    )


def _touch(conversation: Conversation) -> None:
    conversation.updated_at = datetime.now(UTC)

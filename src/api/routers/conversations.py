"""Conversation and message endpoints (owner-scoped)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.auth.deps import get_current_user
from src.db.models import Conversation, Document, Message, User
from src.db.session import get_db
from src.schemas import (
    ConversationListResponse,
    ConversationResponse,
    CreateConversationRequest,
    MessageListResponse,
    MessageResponse,
    SendMessageRequest,
    UpdateConversationRequest,
)
from src.services.conversations import run_conversation_turn, stream_conversation_turn

router = APIRouter(prefix="/conversations")


def _conversation_response(conversation: Conversation) -> ConversationResponse:
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        document_id=conversation.document_id,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


def _message_response(message: Message) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        role=message.role,
        content=message.content,
        confidence_score=message.confidence_score,
        web_search_used=message.web_search_used,
        sources=message.sources or [],
        trace=message.trace or [],
        retrieval_evidence=message.retrieval_evidence or [],
        created_at=message.created_at,
    )


def _get_owned_conversation(db: Session, conversation_id: int, user: User) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return conversation


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: CreateConversationRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    if payload.document_id is not None:
        document = db.get(Document, payload.document_id)
        if document is None or document.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
            )
    conversation = Conversation(
        user_id=user.id,
        title=payload.title,
        document_id=payload.document_id,
    )
    db.add(conversation)
    db.commit()
    return _conversation_response(conversation)


@router.get("", response_model=ConversationListResponse)
def list_conversations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationListResponse:
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return ConversationListResponse(
        items=[_conversation_response(conversation) for conversation in conversations]
    )


@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    return _conversation_response(_get_owned_conversation(db, conversation_id, user))


@router.patch("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: int,
    payload: UpdateConversationRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    conversation = _get_owned_conversation(db, conversation_id, user)
    conversation.title = payload.title
    conversation.updated_at = datetime.now(UTC)
    db.commit()
    return _conversation_response(conversation)


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    conversation = _get_owned_conversation(db, conversation_id, user)
    db.delete(conversation)
    db.commit()


@router.get("/{conversation_id}/messages", response_model=MessageListResponse)
def list_messages(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageListResponse:
    conversation = _get_owned_conversation(db, conversation_id, user)
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.id.asc())
        .all()
    )
    return MessageListResponse(items=[_message_response(message) for message in messages])


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def send_message(
    conversation_id: int,
    payload: SendMessageRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    conversation = _get_owned_conversation(db, conversation_id, user)
    assistant_message = run_conversation_turn(db, conversation, user, payload.content)
    return _message_response(assistant_message)


@router.post("/{conversation_id}/messages/stream")
def send_message_stream(
    conversation_id: int,
    payload: SendMessageRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Same as ``send_message`` but answers are streamed as Server-Sent Events.

    Emits ``data: {"type": "delta", "content": ...}`` frames followed by a
    final ``data: {"type": "done", "message": {...}}`` frame (or an error
    frame when the model fails mid-stream).
    """
    conversation = _get_owned_conversation(db, conversation_id, user)

    def event_stream() -> Iterator[str]:
        for event in stream_conversation_turn(db, conversation, user, payload.content):
            payload_out: dict[str, Any] = event
            if event.get("type") == "done" and event.get("message") is not None:
                serialized = _message_response(event["message"]).model_dump(mode="json")
                payload_out = {**event, "message": serialized}
            yield f"data: {json.dumps(payload_out)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

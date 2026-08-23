"""Agent workflow state definitions."""

from __future__ import annotations

from typing import TypedDict

from langchain_core.documents import Document


class AgentState(TypedDict, total=False):
    query: str
    rewritten_query: str | None
    documents: list[Document]
    web_search_needed: bool
    web_search_used: bool
    retry_count: int
    generation: str
    confidence_score: float
    sources: list[str]
    retrieval_trace: list[str]
    errors: list[str]

"""Cohere Rerank v3 wrapper."""

from __future__ import annotations

import cohere
from langchain_core.documents import Document

from src.config import Settings, get_settings
from src.exceptions import RerankError


class CohereReranker:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def rerank(
        self, query: str, documents: list[Document], *, top_k: int | None = None
    ) -> list[Document]:
        if not documents:
            return []
        api_key = self.settings.require_cohere()
        limit = top_k or self.settings.rerank_top_k
        try:
            client = cohere.Client(api_key=api_key, timeout=self.settings.request_timeout_seconds)
            response = client.rerank(
                model=self.settings.rerank_model,
                query=query,
                documents=[doc.page_content for doc in documents],
                top_n=min(limit, len(documents)),
            )
        except Exception as exc:  # pragma: no cover - external service specific
            raise RerankError("Cohere reranking failed") from exc

        reranked: list[Document] = []
        for item in response.results:
            original = documents[item.index]
            metadata = {**original.metadata, "rerank_score": float(item.relevance_score)}
            reranked.append(Document(page_content=original.page_content, metadata=metadata))
        return reranked


class PassthroughReranker:
    """Test and degradation helper that keeps document order stable."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def rerank(
        self, query: str, documents: list[Document], *, top_k: int | None = None
    ) -> list[Document]:
        del query
        limit = top_k or self.settings.rerank_top_k
        return documents[:limit]

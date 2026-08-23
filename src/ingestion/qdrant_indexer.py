"""Qdrant vector indexing for child chunks."""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from uuid import UUID

from langchain_core.documents import Document
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from src.config import Settings, get_settings
from src.exceptions import IndexingError
from src.pipeline.embeddings import build_embeddings


def _batched(items: list[Document], batch_size: int) -> Iterable[list[Document]]:
    for index in range(0, len(items), batch_size):
        yield items[index : index + batch_size]


def _as_point_id(raw: object, content: str) -> UUID:
    try:
        return UUID(hex=str(raw)[:32])
    except (ValueError, TypeError):
        return uuid.uuid5(uuid.NAMESPACE_DNS, content)


class QdrantIndexer:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = QdrantClient(
            url=self.settings.qdrant_url, timeout=self.settings.request_timeout_seconds
        )

    def ensure_collection(self) -> None:
        try:
            collections = self.client.get_collections().collections
            exists = any(item.name == self.settings.qdrant_collection for item in collections)
            if exists:
                return
            self.client.create_collection(
                collection_name=self.settings.qdrant_collection,
                vectors_config=qmodels.VectorParams(
                    size=self.settings.embedding_dimensions,
                    distance=qmodels.Distance.COSINE,
                ),
            )
        except Exception as exc:  # pragma: no cover - external service specific
            raise IndexingError("Unable to ensure Qdrant collection") from exc

    def upsert_documents(self, documents: list[Document], *, batch_size: int = 64) -> int:
        if not documents:
            return 0
        self.ensure_collection()
        embeddings = build_embeddings(self.settings)

        indexed = 0
        try:
            for batch in _batched(documents, batch_size):
                vectors = embeddings.embed_documents([doc.page_content for doc in batch])
                points = []
                for doc, vector in zip(batch, vectors, strict=True):
                    point_id = _as_point_id(
                        doc.metadata.get("child_id") or doc.metadata.get("content_hash"),
                        doc.page_content,
                    )
                    payload = {**doc.metadata, "text": doc.page_content}
                    points.append(qmodels.PointStruct(id=point_id, vector=vector, payload=payload))
                self.client.upsert(collection_name=self.settings.qdrant_collection, points=points)
                indexed += len(batch)
        except Exception as exc:  # pragma: no cover - external service specific
            raise IndexingError("Unable to index documents into Qdrant") from exc
        return indexed

    def ready(self) -> tuple[bool, str | None]:
        try:
            self.client.get_collections()
            return True, None
        except Exception as exc:  # pragma: no cover - external service specific
            return False, str(exc)

    def delete_by_document(self, document_id: str) -> int:
        """Delete all points whose payload references the given document."""
        try:
            result = self.client.delete(
                collection_name=self.settings.qdrant_collection,
                points_selector=qmodels.FilterSelector(
                    filter=qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key="document_id", match=qmodels.MatchValue(value=document_id)
                            )
                        ]
                    )
                ),
            )
            return 0 if result is None else 1
        except Exception as exc:  # pragma: no cover - external service specific
            raise IndexingError("Unable to delete documents from Qdrant") from exc

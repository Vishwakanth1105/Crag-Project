"""Hybrid vector and graph retrieval."""

from __future__ import annotations

import re

from langchain_core.documents import Document
from neo4j import GraphDatabase
from qdrant_client import QdrantClient

from src.config import Settings, get_settings
from src.exceptions import RetrievalError
from src.pipeline.embeddings import build_embeddings

ENTITY_PATTERN = re.compile(r"\b[A-Z][A-Za-z0-9&.-]*(?:\s+[A-Z][A-Za-z0-9&.-]*){0,4}\b")


def extract_query_entities(query: str, *, limit: int = 8) -> list[str]:
    entities: list[str] = []
    for match in ENTITY_PATTERN.findall(query):
        value = match.strip()
        if len(value) > 2 and value.lower() not in {"what", "when", "where", "which", "tell"}:
            entities.append(value)
    deduped = list(dict.fromkeys(entities))
    if deduped:
        return deduped[:limit]
    return [token for token in re.findall(r"[A-Za-z0-9_-]{4,}", query)[:limit]]


class HybridRetriever:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.qdrant = QdrantClient(
            url=self.settings.qdrant_url, timeout=self.settings.request_timeout_seconds
        )
        self.neo4j_driver = GraphDatabase.driver(
            self.settings.neo4j_uri,
            auth=(self.settings.neo4j_user, self.settings.neo4j_password),
        )

    def close(self) -> None:
        self.neo4j_driver.close()

    def retrieve(self, query: str, *, trace: list[str] | None = None) -> list[Document]:
        trace = trace if trace is not None else []
        documents: list[Document] = []
        vector_error: Exception | None = None
        graph_error: Exception | None = None

        try:
            vector_documents = self.vector_search(query)
            trace.append(f"vector_search: {len(vector_documents)} results")
            documents.extend(vector_documents)
        except Exception as exc:  # pragma: no cover - external service specific
            vector_error = exc
            trace.append(f"vector_search_error: {type(exc).__name__}")

        try:
            graph_documents = self.graph_search(query)
            trace.append(f"graph_search: {len(graph_documents)} results")
            documents.extend(graph_documents)
        except Exception as exc:  # pragma: no cover - external service specific
            graph_error = exc
            trace.append(f"graph_search_error: {type(exc).__name__}")

        if not documents and (vector_error or graph_error):
            raise RetrievalError("Hybrid retrieval failed to return documents")
        return self._dedupe_documents(documents)

    def vector_search(self, query: str) -> list[Document]:
        embeddings = build_embeddings(self.settings)
        query_vector = embeddings.embed_query(query)
        response = self.qdrant.query_points(
            collection_name=self.settings.qdrant_collection,
            query=query_vector,
            limit=self.settings.vector_top_k,
            with_payload=True,
        )
        documents: list[Document] = []
        for result in response.points:
            payload = result.payload or {}
            text = str(payload.get("text", ""))
            if not text.strip():
                continue
            metadata = {**payload, "score": float(result.score), "retrieval_source": "vector"}
            documents.append(Document(page_content=text, metadata=metadata))
        return documents

    def graph_search(self, query: str) -> list[Document]:
        entities = extract_query_entities(query)
        if not entities:
            return []
        cypher = """
        UNWIND $entities AS entity
        MATCH path = (start:Entity)-[*1..2]-(neighbor:Entity)
        WHERE toLower(start.name) CONTAINS toLower(entity)
        WITH path LIMIT $limit
        UNWIND relationships(path) AS rel
        WITH DISTINCT startNode(rel) AS s, type(rel) AS relation, endNode(rel) AS o, rel
        RETURN s.name AS subject, relation, o.name AS object,
               rel.source AS source, rel.document_id AS document_id,
               coalesce(rel.confidence, 0.5) AS score
        LIMIT $limit
        """
        documents: list[Document] = []
        with self.neo4j_driver.session() as session:
            rows = session.run(cypher, entities=entities, limit=self.settings.graph_top_k)
            for row in rows:
                subject = row["subject"]
                relation = row["relation"].replace("_", " ").lower()
                obj = row["object"]
                text = f"Graph fact: {subject} {relation} {obj}."
                documents.append(
                    Document(
                        page_content=text,
                        metadata={
                            "retrieval_source": "graph",
                            "source_type": "graph",
                            "source": row.get("source") or "neo4j",
                            "document_id": row.get("document_id"),
                            "score": float(row.get("score") or 0.5),
                        },
                    )
                )
        return documents

    @staticmethod
    def _dedupe_documents(documents: list[Document]) -> list[Document]:
        seen: set[str] = set()
        deduped: list[Document] = []
        for document in documents:
            key = str(document.metadata.get("content_hash") or document.page_content[:500])
            if key in seen:
                continue
            seen.add(key)
            deduped.append(document)
        return deduped

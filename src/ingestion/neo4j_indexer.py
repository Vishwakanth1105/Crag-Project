"""Neo4j graph indexing with structured LLM triplet extraction."""

from __future__ import annotations

import re
from typing import cast

from langchain_core.documents import Document
from neo4j import GraphDatabase
from pydantic import BaseModel, Field

from src.config import Settings, get_settings
from src.exceptions import IndexingError
from src.pipeline.llm import build_chat_model


class KnowledgeTriple(BaseModel):
    subject: str = Field(min_length=1)
    relation: str = Field(min_length=1)
    object: str = Field(min_length=1)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class ExtractedTriples(BaseModel):
    triples: list[KnowledgeTriple] = Field(default_factory=list)


def _normalize_relation(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_]+", "_", value.upper()).strip("_")
    return normalized or "RELATED_TO"


def _normalize_entity(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


class Neo4jIndexer:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.driver = GraphDatabase.driver(
            self.settings.neo4j_uri,
            auth=(self.settings.neo4j_user, self.settings.neo4j_password),
        )

    def close(self) -> None:
        self.driver.close()

    def ready(self) -> tuple[bool, str | None]:
        try:
            self.driver.verify_connectivity()
            return True, None
        except Exception as exc:  # pragma: no cover - external service specific
            return False, str(exc)

    def extract_triples(self, text: str) -> list[KnowledgeTriple]:
        llm = build_chat_model(self.settings, num_ctx=4096)
        structured = llm.with_structured_output(ExtractedTriples)
        prompt = (
            "Extract factual knowledge graph triples from the text. "
            "Use concise entity names and relation verbs. Return only grounded triples.\n\n"
            f"Text:\n{text[:12000]}"
        )
        result = cast(ExtractedTriples, structured.invoke(prompt))
        return [
            triple
            for triple in result.triples
            if triple.confidence >= self.settings.min_triple_confidence
            and _normalize_entity(triple.subject)
            and _normalize_entity(triple.object)
        ]

    def index_documents(self, documents: list[Document]) -> int:
        total = 0
        try:
            with self.driver.session() as session:
                for document in documents:
                    triples = self.extract_triples(document.page_content)
                    for triple in triples:
                        relation = _normalize_relation(triple.relation)
                        query = (
                            "MERGE (s:Entity {name: $subject}) "
                            "MERGE (o:Entity {name: $object}) "
                            f"MERGE (s)-[r:{relation}]->(o) "
                            "SET r.source = $source, r.document_id = $document_id, "
                            "r.confidence = $confidence, r.updated_at = datetime()"
                        )
                        session.run(
                            query,
                            subject=_normalize_entity(triple.subject),
                            object=_normalize_entity(triple.object),
                            source=document.metadata.get("source", "unknown"),
                            document_id=document.metadata.get("document_id"),
                            confidence=triple.confidence,
                        )
                        total += 1
        except Exception as exc:  # pragma: no cover - external service specific
            raise IndexingError("Unable to index graph relationships into Neo4j") from exc
        return total

    def delete_by_document(self, document_id: str) -> int:
        """Remove relationships and orphaned entities tagged with a document."""
        deleted = 0
        try:
            with self.driver.session() as session:
                result = session.run(
                    "MATCH ()-[r]->() WHERE r.document_id = $document_id "
                    "WITH r DELETE r RETURN count(*) AS removed",
                    document_id=document_id,
                )
                row = result.single()
                deleted = int(row["removed"]) if row is not None else 0
                session.run("MATCH (e:Entity) WHERE NOT (e)--() DELETE e")
        except Exception as exc:  # pragma: no cover - external service specific
            raise IndexingError("Unable to delete graph relationships from Neo4j") from exc
        return deleted

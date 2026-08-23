"""Shared fixtures for the agentic graph RAG test suite.

Tests run fully offline: no API keys, no Docker, no Qdrant/Neo4j/MinIO. All
provider and store boundaries are injected as fakes through NodeDependencies,
and the application datastore uses a temporary SQLite file.
"""

from __future__ import annotations

import pytest
from langchain_core.documents import Document

from src.agents.graph import run_agent
from src.agents.nodes import NodeDependencies
from src.pipeline.evaluator import DocumentGrade, GradeDocuments, HeuristicEvaluator
from src.pipeline.reranker import PassthroughReranker


@pytest.fixture
def db_session_factory(tmp_path, monkeypatch: pytest.MonkeyPatch):
    """SQLite-backed session factory with a clean engine per test."""
    import src.db.session as db_session
    from src.config import get_settings
    from src.db.models import Base

    url = f"sqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    db_session.reset_engine()
    Base.metadata.create_all(bind=db_session.get_engine())
    factory = db_session.get_session_factory()
    yield factory
    db_session.reset_engine()
    get_settings.cache_clear()


@pytest.fixture
def client(db_session_factory):
    """FastAPI TestClient with the DB dependency overridden to test SQLite."""
    from fastapi.testclient import TestClient

    from src.api.app import app
    from src.db.session import get_db

    def _override_db():
        session = db_session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


class FakeRetriever:
    """Returns a configurable set of documents without touching stores."""

    def __init__(self, documents: list[Document] | None = None) -> None:
        self._documents = documents or []

    def retrieve(self, query: str, *, trace: list[str] | None = None) -> list[Document]:
        if trace is not None:
            trace.append(f"fake_retrieve: {len(self._documents)} results")
        return self._documents


class SelectiveEvaluator(HeuristicEvaluator):
    """Heuristic grader with deterministic, per-test relevance behavior."""

    def __init__(self, *, relevance: float = 0.8) -> None:
        super().__init__()
        self._relevance = relevance

    def grade(self, query: str, documents: list[Document]) -> GradeDocuments:
        grades: list[DocumentGrade] = []
        for document in documents:
            binary = "yes" if document.metadata.get("_relevant", True) else "no"
            score = self._relevance if binary == "yes" else 0.0
            document.metadata["grade_binary_score"] = binary
            document.metadata["grade_relevance_score"] = score
            grades.append(DocumentGrade(binary_score=binary, relevance_score=score, reason="test"))
        relevant_count = sum(1 for g in grades if g.binary_score == "yes")
        average = sum(g.relevance_score for g in grades) / len(grades) if grades else 0.0
        return GradeDocuments(
            grades=grades, relevant_count=relevant_count, average_relevance=average
        )


def _document(text: str, *, source: str = "test.txt", relevant: bool = True) -> Document:
    return Document(
        page_content=text,
        metadata={
            "source": source,
            "source_type": "document",
            "_relevant": relevant,
        },
    )


@pytest.fixture
def relevant_documents() -> list[Document]:
    return [
        _document("LangGraph is a library for building stateful, agentic workflows."),
        _document("Qdrant is an open-source vector database optimized for retrieval."),
    ]


@pytest.fixture
def irrelevant_documents() -> list[Document]:
    return [
        _document("The weather in Oslo was rainy all weekend.", relevant=False),
        _document("Cats sleep roughly 16 hours every day.", relevant=False),
    ]


@pytest.fixture
def deps() -> NodeDependencies:
    retriever = FakeRetriever()
    return NodeDependencies(
        retriever=retriever,
        reranker=PassthroughReranker(),
        evaluator=SelectiveEvaluator(),
    )


def make_offline_agent(documents: list[Document] | None = None) -> NodeDependencies:
    return NodeDependencies(
        retriever=FakeRetriever(documents),
        reranker=PassthroughReranker(),
        evaluator=SelectiveEvaluator(),
    )


def run_offline(query: str, documents: list[Document] | None = None) -> dict:
    return run_agent(query, make_offline_agent(documents))

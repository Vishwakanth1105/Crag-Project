"""Tests for the local/gemini provider factories and dependency wiring."""

from __future__ import annotations

import pytest
from langchain_core.embeddings import Embeddings
from pydantic import ValidationError

from src.config import Settings
from src.exceptions import ConfigurationError
from src.pipeline import embeddings as embeddings_module
from src.pipeline.embeddings import build_embeddings
from src.pipeline.llm import build_chat_model


class _DummyEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 4 for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.0] * 4


def _local_settings() -> Settings:
    return Settings(llm_provider="local", gemini_api_key=None)


def _gemini_settings(*, api_key: str | None = None) -> Settings:
    return Settings(llm_provider="gemini", gemini_api_key=api_key)


def test_local_chat_model_uses_ollama() -> None:
    model = build_chat_model(_local_settings())
    assert type(model).__name__ == "ChatOllama"


def test_gemini_chat_model_requires_api_key() -> None:
    with pytest.raises(ConfigurationError):
        build_chat_model(_gemini_settings(api_key=None))


def test_gemini_chat_model_with_key() -> None:
    model = build_chat_model(_gemini_settings(api_key="test-key"))
    assert type(model).__name__ == "ChatGoogleGenerativeAI"


def test_unknown_provider_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(llm_provider="openai")


def test_embeddings_instances_cached_per_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Settings] = []

    def fake_create(settings: Settings) -> Embeddings:
        calls.append(settings)
        return _DummyEmbeddings()

    monkeypatch.setattr(embeddings_module, "_create_embeddings", fake_create)
    monkeypatch.setattr(embeddings_module, "_EMBEDDINGS_CACHE", {})

    local = build_embeddings(_local_settings())
    assert build_embeddings(_local_settings()) is local
    assert len(calls) == 1

    gemini = build_embeddings(_gemini_settings(api_key="k"))
    assert gemini is not local
    assert len(calls) == 2


def test_local_dependencies_use_heuristic_grading_without_heuristic_answers() -> None:
    from src.agents.nodes import NodeDependencies
    from src.pipeline.evaluator import HeuristicEvaluator
    from src.pipeline.reranker import PassthroughReranker
    from tests.conftest import FakeRetriever

    deps = NodeDependencies(
        settings=_local_settings(),
        retriever=FakeRetriever(),
        reranker=PassthroughReranker(),
    )
    assert isinstance(deps.evaluator, HeuristicEvaluator)
    # Answers still go through the local chat model (Ollama), not the
    # deterministic composer.
    assert deps.is_heuristic is False


def test_gemini_dependencies_fall_back_to_deterministic_answers_without_key() -> None:
    from src.agents.nodes import NodeDependencies
    from src.pipeline.evaluator import DocumentEvaluator
    from src.pipeline.reranker import PassthroughReranker
    from tests.conftest import FakeRetriever

    deps = NodeDependencies(
        settings=_gemini_settings(api_key=None),
        retriever=FakeRetriever(),
        reranker=PassthroughReranker(),
    )
    assert isinstance(deps.evaluator, DocumentEvaluator)
    assert deps.is_heuristic is True

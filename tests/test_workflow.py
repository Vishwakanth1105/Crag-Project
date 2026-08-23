"""Offline workflow tests for the agentic CRAG pipeline."""

from __future__ import annotations

from langchain_core.documents import Document

from tests.conftest import run_offline


def test_answers_with_relevant_documents(relevant_documents: list[Document]) -> None:
    state = run_offline("What does LangGraph do?", relevant_documents)

    assert state["query"] == "What does LangGraph do?"
    assert state["generation"]
    assert state["confidence_score"] > 0.0
    assert state["web_search_used"] is False
    assert state["retry_count"] == 0
    assert any("grade:" in entry for entry in state["retrieval_trace"])
    assert state["sources"]


def test_falls_back_to_web_search_when_nothing_relevant(
    irrelevant_documents: list[Document],
) -> None:
    state = run_offline("When did the Ming dynasty begin?", irrelevant_documents)

    assert state["web_search_used"] is False  # no TAVILY_API_KEY in tests
    trace = state["retrieval_trace"]
    assert isinstance(trace, list)
    assert any("web_search:" in str(x) for x in trace)
    assert "confidence_score" in state


def test_validation_rejects_empty_query() -> None:
    state = run_offline("   ")

    assert state["generation"] == "No question was provided."
    assert state["confidence_score"] == 0.0
    assert state["errors"] == ["empty_query"]


def test_validation_rejects_oversized_query() -> None:
    state = run_offline("a" * 5000)

    assert state["generation"] == "Question is too long."
    assert state["errors"] == ["query_too_long"]


def test_retry_path_runs_without_hitting_provider(
    irrelevant_documents: list[Document],
) -> None:
    state = run_offline("What is the capital of Atlantis?", irrelevant_documents)

    assert state["retry_count"] == 2
    steps = [t.split(":")[0] for t in state["retrieval_trace"]]
    assert steps.count("rewrite_query") == 2
    assert "web_search" in steps


class FailingRetriever:
    def retrieve(self, query: str, *, trace: list[str] | None = None) -> list[Document]:
        del query
        if trace is not None:
            trace.append("fake_retrieve: failed")
        from src.exceptions import RetrievalError

        raise RetrievalError("Hybrid retrieval failed to return documents")


def test_retriever_failure_degrades_gracefully() -> None:
    from tests.conftest import make_offline_agent

    deps = make_offline_agent()
    deps.retriever = FailingRetriever()  # type: ignore[attr-defined]
    from src.agents.graph import run_agent

    state = run_agent("What is the capital of Atlantis?", deps)

    assert state["generation"]
    assert any("retrieve_error:" in entry for entry in state["retrieval_trace"])
    assert "web_search" in [t.split(":")[0] for t in state["retrieval_trace"]]

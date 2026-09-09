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
    def retrieve(
        self,
        query: str,
        *,
        trace: list[str] | None = None,
        document_id: str | None = None,
    ) -> list[Document]:
        del query
        del document_id
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


class RecordingRetriever:
    def __init__(self, documents: list[Document] | None = None) -> None:
        self._documents = documents or []
        self.document_id: str | None = None

    def retrieve(
        self,
        query: str,
        *,
        trace: list[str] | None = None,
        document_id: str | None = None,
    ) -> list[Document]:
        del query
        self.document_id = document_id
        if trace is not None:
            trace.append("fake_retrieve: recorded")
        return self._documents


def test_retrieval_is_scoped_to_document() -> None:
    from tests.conftest import make_offline_agent

    deps = make_offline_agent([Document(page_content="Relevant text about hooks.", metadata={})])
    retriever = RecordingRetriever()
    deps.retriever = retriever  # type: ignore[attr-defined]
    from src.agents.graph import run_agent

    state = run_agent("What is a hook?", deps, document_id="doc-42")
    assert retriever.document_id == "doc-42"
    assert state["generation"]

    retriever.document_id = None
    run_agent("What is a hook?", deps)
    assert retriever.document_id is None


def test_capture_generation_only_skips_model_call(
    relevant_documents: list[Document],
) -> None:
    state = run_offline("What does LangGraph do?", relevant_documents, capture_generation_only=True)

    assert state["generation"] == ""
    assert state["documents"]
    assert state["sources"]
    assert state["confidence_score"] > 0.0
    assert any("grade:" in entry for entry in state["retrieval_trace"])


def test_build_answer_prompt_trims_context_chunks() -> None:
    from src.agents.nodes import build_answer_prompt
    from src.config import Settings

    documents = [Document(page_content="x" * 500, metadata={})]
    settings = Settings(max_context_chars=25)
    prompt = build_answer_prompt("What is this?", documents, settings)

    assert "Question: What is this?" in prompt
    assert "[1] " in prompt
    trimmed = prompt.split("[1] ", 1)[1]
    assert len(trimmed.strip("…")) == 25
    assert "x" * 500 not in prompt

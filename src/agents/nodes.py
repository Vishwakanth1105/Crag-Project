"""CRAG workflow nodes for the LangGraph state machine.

Every node follows the signature ``fn(state, deps)`` where ``deps`` carries
the injected components (retriever, reranker, evaluator, settings). This keeps
the workflow fully dependency-injectable so tests can substitute fakes without
real provider keys or live databases.
"""

from __future__ import annotations

from collections.abc import Callable

from langchain_core.documents import Document

from src.agents.state import AgentState
from src.config import Settings, get_settings
from src.exceptions import ConfigurationError
from src.pipeline.evaluator import (
    DocumentEvaluator,
    GradeDocuments,
    HeuristicEvaluator,
)
from src.pipeline.llm import build_chat_model
from src.pipeline.reranker import CohereReranker, PassthroughReranker
from src.pipeline.retrievers import HybridRetriever


class NodeDependencies:
    """Holds the concrete components used by the workflow nodes."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        retriever: HybridRetriever | None = None,
        reranker: CohereReranker | PassthroughReranker | None = None,
        evaluator: DocumentEvaluator | HeuristicEvaluator | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.retriever = retriever or HybridRetriever(self.settings)
        self.reranker = reranker or (
            CohereReranker(self.settings)
            if self.settings.cohere_api_key
            else PassthroughReranker(self.settings)
        )
        if evaluator is not None:
            self.evaluator = evaluator
            # Explicit injection (tests/offline runs) keeps the legacy contract:
            # a heuristic grader implies deterministic, provider-free answers.
            self._heuristic_answers = isinstance(evaluator, HeuristicEvaluator)
        elif self.settings.use_local_llm:
            # Local MVP mode: deterministic zero-cost grading; answers still
            # come from the local chat model (Ollama).
            self.evaluator = HeuristicEvaluator(self.settings)
            self._heuristic_answers = False
        else:
            self.evaluator = DocumentEvaluator(self.settings)
            self._heuristic_answers = not self.settings.gemini_api_key

    @property
    def is_heuristic(self) -> bool:
        """True when answers should use the deterministic offline composer."""
        return self._heuristic_answers


def validate_query(state: AgentState, deps: NodeDependencies) -> AgentState:
    query = (state.get("query") or "").strip()
    if not query:
        return _fail_without_answer(state, "No question was provided.", "empty_query")
    if len(query) > 4000:
        return _fail_without_answer(state, "Question is too long.", "query_too_long")
    state["query"] = query
    state["web_search_needed"] = False
    state["web_search_used"] = False
    state["retry_count"] = state.get("retry_count") or 0
    return state


def retrieve(state: AgentState, deps: NodeDependencies) -> AgentState:
    query = state.get("rewritten_query") or state.get("query") or ""
    trace = state.setdefault("retrieval_trace", [])
    try:
        state["documents"] = deps.retriever.retrieve(query, trace=trace)
    except Exception as exc:
        state["documents"] = []
        trace.append(f"retrieve_error: {type(exc).__name__}")
    return state


def rerank(state: AgentState, deps: NodeDependencies) -> AgentState:
    query = state.get("query") or ""
    documents = state.get("documents") or []
    if not documents:
        return state
    state["documents"] = deps.reranker.rerank(query, documents)
    state.setdefault("retrieval_trace", []).append(f"rerank: {len(state['documents'])} documents")
    return state


def grade_documents(state: AgentState, deps: NodeDependencies) -> AgentState:
    query = state.get("query") or ""
    documents = state.get("documents") or []
    graded = deps.evaluator.grade(query, documents)
    relevant = [
        document
        for document, grade in zip(documents, graded.grades, strict=True)
        if grade.binary_score == "yes"
    ]
    state["documents"] = relevant
    state["confidence_score"] = _average_relevance(graded)
    state.setdefault("retrieval_trace", []).append(
        f"grade: {graded.relevant_count}/{len(graded.grades)} relevant, "
        f"avg_relevance={graded.average_relevance:.2f}"
    )
    if graded.relevant_count == 0:
        state["web_search_needed"] = True
    return state


def _average_relevance(graded: GradeDocuments) -> float:
    if not graded.grades:
        return 0.0
    return sum(grade.relevance_score for grade in graded.grades) / len(graded.grades)


def rewrite_query(state: AgentState, deps: NodeDependencies) -> AgentState:
    query = state.get("query") or ""
    state["rewritten_query"] = f"{query} expanded context relationships entities"
    state["retry_count"] = (state.get("retry_count") or 0) + 1
    state.setdefault("retrieval_trace", []).append(f"rewrite_query: retry #{state['retry_count']}")
    return state


def web_search(state: AgentState, deps: NodeDependencies) -> AgentState:
    query = (state.get("rewritten_query") or state.get("query")) or ""
    trace = state.setdefault("retrieval_trace", [])
    state["web_search_used"] = False
    if not deps.settings.tavily_api_key:
        trace.append("web_search: skipped (no TAVILY_API_KEY)")
        return _empty_docs(state)
    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=deps.settings.tavily_api_key)
        response = client.search(query=query, max_results=5, search_depth="basic")
        web_documents: list[Document] = []
        for result in response.get("results", []):
            content = (result.get("content") or "").strip()
            if not content:
                continue
            web_documents.append(
                Document(
                    page_content=content,
                    metadata={
                        "retrieval_source": "web",
                        "source_type": "web",
                        "url": result.get("url"),
                        "title": result.get("title"),
                        "score": result.get("score", 0.5),
                    },
                )
            )
        state["documents"] = web_documents
        state["web_search_used"] = bool(web_documents)
        trace.append(f"web_search: {len(web_documents)} results")
    except Exception:
        trace.append("web_search: failed")
        state["documents"] = []
    return state


def _empty_docs(state: AgentState) -> AgentState:
    state["documents"] = []
    return state


def generate(state: AgentState, deps: NodeDependencies) -> AgentState:
    query = state.get("query") or ""
    documents = state.get("documents") or []
    state["generation"] = _build_answer(query, documents, deps)
    state["sources"] = _collect_sources(state)
    state["confidence_score"] = _final_confidence(state)
    return state


def _build_answer(query: str, documents: list[Document], deps: NodeDependencies) -> str:
    if not documents:
        return (
            "I could not find enough relevant context to answer this question, "
            "and web search was unavailable."
        )

    prompt = (
        "Answer the user question using only the provided context. "
        "If the context is insufficient, say so explicitly and do not "
        "fabricate facts. Cite sources by their identifiers when known.\n\n"
        f"Question: {query}\n\nContext:\n"
        + "\n\n".join(f"[{i + 1}] {doc.page_content}" for i, doc in enumerate(documents))
    )

    if deps.is_heuristic:
        return _heuristic_answer(query, documents)

    try:
        llm = build_chat_model(deps.settings, num_ctx=6144)
        return _extract_response_text(llm.invoke(prompt).content)
    except ConfigurationError:
        return _heuristic_answer(query, documents)
    except Exception:
        return (
            "Generation failed, but the following context was retrieved. "
            "Please verify the answer against the provided sources.\n"
            + "\n\n".join(doc.page_content[:500] for doc in documents[:3])
        )


def _extract_response_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(str(text))
        if parts:
            return "\n".join(parts)
    return str(content)


def _heuristic_answer(query: str, documents: list[Document]) -> str:
    del query
    return "Based on the retrieved context:\n\n" + "\n\n".join(
        f"- {doc.page_content[:300]}" for doc in documents[:5]
    )


def _collect_sources(state: AgentState) -> list[str]:
    sources: list[str] = []
    for document in state.get("documents") or []:
        ref = document.metadata.get("url") or document.metadata.get("source")
        if ref and ref not in sources:
            sources.append(str(ref))
    return sources


def _final_confidence(state: AgentState) -> float:
    base = state.get("confidence_score") or 0.0
    if not state.get("documents"):
        return 0.0
    if state.get("web_search_used"):
        base *= 0.7
    return round(min(1.0, max(0.0, base)), 3)


def route_after_validation(state: AgentState) -> str:
    """Short-circuit to the end when validation rejected the query."""
    if state.get("errors"):
        return "end"
    return "retrieve"


def route_after_grade(state: AgentState) -> str:
    if not state.get("documents"):
        max_retries = get_settings().max_retries
        if (state.get("retry_count") or 0) < max_retries:
            return "rewrite_query"
        return "web_search"
    return "generate"


def _fail_without_answer(state: AgentState, message: str, error_code: str) -> AgentState:
    state["generation"] = message
    state["confidence_score"] = 0.0
    state["web_search_used"] = False
    state["errors"] = (state.get("errors") or []) + [error_code]
    return state


NodeFn = Callable[[AgentState, NodeDependencies], AgentState]


def bind_deps(node: NodeFn, deps: NodeDependencies) -> Callable[[AgentState], AgentState]:
    """Adapt a ``(state, deps)`` node into a LangGraph ``(state)`` node."""
    return lambda state: node(state, deps)

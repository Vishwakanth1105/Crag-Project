"""LangGraph state machine for the agentic CRAG workflow."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.agents.nodes import (
    NodeDependencies,
    bind_deps,
    generate,
    grade_documents,
    rerank,
    retrieve,
    rewrite_query,
    route_after_grade,
    route_after_validation,
    validate_query,
    web_search,
)
from src.agents.state import AgentState


def build_agent_graph(
    deps: NodeDependencies | None = None,
) -> CompiledStateGraph[AgentState, None, AgentState, AgentState]:
    """Assemble and return the compiled CRAG state machine.

    ``deps`` may be injected for testing; otherwise a default dependency set
    wired against the configured Qdrant/Neo4j instances is created lazily.
    """
    dependencies = deps or NodeDependencies()

    builder = StateGraph(AgentState)

    # LangGraph 1.x typing does not accept plain callable nodes without a
    # matching input_schema overload; runtime behavior is correct.
    builder.add_node("validate_query", bind_deps(validate_query, dependencies))  # type: ignore[call-overload]
    builder.add_node("retrieve", bind_deps(retrieve, dependencies))  # type: ignore[call-overload]
    builder.add_node("rerank", bind_deps(rerank, dependencies))  # type: ignore[call-overload]
    builder.add_node("grade_documents", bind_deps(grade_documents, dependencies))  # type: ignore[call-overload]
    builder.add_node("rewrite_query", bind_deps(rewrite_query, dependencies))  # type: ignore[call-overload]
    builder.add_node("web_search", bind_deps(web_search, dependencies))  # type: ignore[call-overload]
    builder.add_node("generate", bind_deps(generate, dependencies))  # type: ignore[call-overload]

    builder.add_edge(START, "validate_query")
    builder.add_conditional_edges(
        "validate_query",
        route_after_validation,
        {"retrieve": "retrieve", "end": END},
    )
    builder.add_edge("retrieve", "rerank")
    builder.add_edge("rerank", "grade_documents")
    builder.add_conditional_edges(
        "grade_documents",
        route_after_grade,
        {
            "rewrite_query": "rewrite_query",
            "web_search": "web_search",
            "generate": "generate",
        },
    )
    builder.add_edge("rewrite_query", "retrieve")
    builder.add_edge("web_search", "generate")
    builder.add_edge("generate", END)

    return builder.compile()


def run_agent(query: str, deps: NodeDependencies | None = None) -> dict:
    """Run the full CRAG workflow and return the populated agent state."""
    graph = build_agent_graph(deps)
    result = graph.invoke(AgentState(query=query, retrieval_trace=[], documents=[], errors=[]))
    return dict(result)

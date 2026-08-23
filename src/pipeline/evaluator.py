"""Structured relevance grading for CRAG."""

from __future__ import annotations

from typing import Literal, cast

from langchain_core.documents import Document
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from src.config import Settings, get_settings
from src.exceptions import EvaluationError


class DocumentGrade(BaseModel):
    binary_score: Literal["yes", "no"]
    relevance_score: float = Field(ge=0.0, le=1.0)
    reason: str = ""


class GradeDocuments(BaseModel):
    grades: list[DocumentGrade] = Field(default_factory=list)
    relevant_count: int = 0
    average_relevance: float = 0.0


class BatchGrades(BaseModel):
    """Structured contract for grading every document in a single LLM call."""

    grades: list[DocumentGrade] = Field(default_factory=list)


class DocumentEvaluator:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def grade(self, query: str, documents: list[Document]) -> GradeDocuments:
        if not documents:
            return GradeDocuments()
        self.settings.require_gemini()
        try:
            llm = ChatGoogleGenerativeAI(
                model=self.settings.evaluation_model,
                api_key=self.settings.gemini_api_key,
                temperature=0,
                timeout=self.settings.request_timeout_seconds,
            )
            structured = llm.with_structured_output(BatchGrades)
            prompt = (
                "Grade whether each document is relevant to the user question. "
                "Return yes only when a document contains evidence that can help answer. "
                "Provide exactly one grade entry per document, in order.\n\n"
                f"Question: {query}\n\n"
                + "\n\n".join(
                    f"[{index}] {document.page_content[:1200]}"
                    for index, document in enumerate(documents, start=1)
                )
            )
            result = cast(BatchGrades, structured.invoke(prompt))
            grades = _normalize_grades(result.grades, len(documents))
            for document, grade in zip(documents, grades, strict=True):
                document.metadata["grade_binary_score"] = grade.binary_score
                document.metadata["grade_relevance_score"] = grade.relevance_score
                document.metadata["grade_reason"] = grade.reason
        except Exception as exc:  # pragma: no cover - external service specific
            raise EvaluationError("Document relevance grading failed") from exc

        relevant_count = sum(1 for grade in grades if grade.binary_score == "yes")
        average = sum(grade.relevance_score for grade in grades) / len(grades)
        return GradeDocuments(
            grades=grades, relevant_count=relevant_count, average_relevance=average
        )


def _normalize_grades(grades: list[DocumentGrade], expected: int) -> list[DocumentGrade]:
    """Pad missing grades so the workflow can zip documents 1:1 with grades."""
    normalized = list(grades[:expected])
    while len(normalized) < expected:
        normalized.append(
            DocumentGrade(binary_score="no", relevance_score=0.0, reason="missing grade")
        )
    return normalized


class HeuristicEvaluator:
    """Deterministic evaluator used by tests and as a safe local fallback."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def grade(self, query: str, documents: list[Document]) -> GradeDocuments:
        query_terms = {term.lower() for term in query.split() if len(term) > 3}
        grades: list[DocumentGrade] = []
        for document in documents:
            content = document.page_content.lower()
            overlap = sum(1 for term in query_terms if term in content)
            score = min(1.0, overlap / max(1, len(query_terms)))
            binary: Literal["yes", "no"] = "yes" if score >= 0.2 else "no"
            document.metadata["grade_binary_score"] = binary
            document.metadata["grade_relevance_score"] = score
            grades.append(
                DocumentGrade(binary_score=binary, relevance_score=score, reason="heuristic")
            )
        relevant_count = sum(1 for grade in grades if grade.binary_score == "yes")
        average = sum(grade.relevance_score for grade in grades) / len(grades) if grades else 0.0
        return GradeDocuments(
            grades=grades, relevant_count=relevant_count, average_relevance=average
        )

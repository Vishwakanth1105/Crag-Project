"""Provider-agnostic embedding factory with process-wide instance caching.

Local models (sentence-transformers) are loaded into memory on construction,
so instances are cached per (provider, model) pair and shared between the
retriever and the indexer within a single process.
"""

from __future__ import annotations

from langchain_core.embeddings import Embeddings

from src.config import Settings

_EMBEDDINGS_CACHE: dict[tuple[str, str], Embeddings] = {}

BGE_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "


def build_embeddings(settings: Settings) -> Embeddings:
    """Return the cached embeddings instance for the configured provider."""
    if settings.use_local_llm:
        key = ("local", settings.local_embedding_model)
    else:
        key = ("gemini", settings.embedding_model)
    if key not in _EMBEDDINGS_CACHE:
        _EMBEDDINGS_CACHE[key] = _create_embeddings(settings)
    return _EMBEDDINGS_CACHE[key]


def _create_embeddings(settings: Settings) -> Embeddings:
    if settings.use_local_llm:
        from langchain_huggingface import HuggingFaceEmbeddings

        inner: Embeddings = HuggingFaceEmbeddings(
            model_name=settings.local_embedding_model,
            encode_kwargs={"normalize_embeddings": True},
        )
        if "bge" in settings.local_embedding_model.lower():
            return _QueryInstructionEmbeddings(inner, BGE_QUERY_INSTRUCTION)
        return inner

    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    from pydantic import SecretStr

    return GoogleGenerativeAIEmbeddings(
        model=settings.embedding_model,
        api_key=SecretStr(settings.require_gemini()),
        output_dimensionality=settings.embedding_dimensions,
    )


class _QueryInstructionEmbeddings(Embeddings):
    """Prefixes search instructions to queries only (bge convention)."""

    def __init__(self, inner: Embeddings, instruction: str) -> None:
        self._inner = inner
        self._instruction = instruction

    def embed_query(self, text: str) -> list[float]:
        return self._inner.embed_query(f"{self._instruction}{text}")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._inner.embed_documents(texts)

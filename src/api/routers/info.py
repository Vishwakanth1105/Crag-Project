"""Runtime model information for the UI (active LLM provider and models)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.auth.deps import get_current_user
from src.config import get_settings
from src.db.models import User
from src.schemas import ChatModelInfo, IngestionModelInfo, ModelsInfoResponse

router = APIRouter(prefix="/info")


@router.get("/models", response_model=ModelsInfoResponse)
def get_models_info(user: User = Depends(get_current_user)) -> ModelsInfoResponse:
    settings = get_settings()
    provider = settings.llm_provider
    if settings.use_local_llm:
        return ModelsInfoResponse(
            chat=ChatModelInfo(
                generation_model=settings.ollama_model,
                embedding_model=settings.local_embedding_model,
                rerank_model=settings.rerank_model if settings.cohere_api_key else "none",
                grader_model="heuristic",
                provider=provider,
            ),
            ingestion=IngestionModelInfo(
                extraction_model=settings.ollama_model,
                embedding_model=settings.local_embedding_model,
                provider=provider,
            ),
        )
    return ModelsInfoResponse(
        chat=ChatModelInfo(
            generation_model=settings.generation_model,
            embedding_model=f"{settings.embedding_model} ({settings.embedding_dimensions}d)",
            rerank_model=settings.rerank_model if settings.cohere_api_key else "none",
            grader_model=settings.evaluation_model,
            provider=provider,
        ),
        ingestion=IngestionModelInfo(
            extraction_model=settings.evaluation_model,
            embedding_model=settings.embedding_model,
            provider=provider,
        ),
    )

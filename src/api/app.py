"""FastAPI application exposing health/readiness plus the v1 API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy import text

from src.api.routers import v1
from src.config import get_settings
from src.ingestion import neo4j_indexer, qdrant_indexer
from src.schemas import DependencyStatus, HealthResponse, ReadinessResponse
from src.storage.minio_client import StorageClient

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        StorageClient(settings).ensure_bucket()
    except Exception as exc:  # pragma: no cover - external service specific
        # Object storage may be briefly unavailable at boot; /ready reports it.
        print(f"minio bucket setup deferred: {type(exc).__name__}")
    yield


app = FastAPI(
    title="Agentic Graph RAG API",
    version="0.1.0",
    description="CRAG + GraphRAG retrieval augmentation service.",
    lifespan=lifespan,
)

if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs", status_code=status.HTTP_307_TEMPORARY_REDIRECT)


app.include_router(v1.router, prefix="/api/v1", tags=["v1"])


@app.get("/health", response_model=HealthResponse, tags=["ops"])
def health() -> HealthResponse:
    return HealthResponse(status="ok")


def _mysql_ready() -> tuple[bool, str | None]:
    try:
        from src.db.session import get_engine

        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:  # pragma: no cover - external service specific
        return False, str(exc)


def _minio_ready() -> tuple[bool, str | None]:
    return StorageClient(settings).ready()


@app.get("/ready", response_model=ReadinessResponse, tags=["ops"])
def readiness() -> ReadinessResponse:
    qdrant = qdrant_indexer.QdrantIndexer(settings)
    neo4j = neo4j_indexer.Neo4jIndexer(settings)
    vector_ready, vector_detail = qdrant.ready()
    graph_ready, graph_detail = neo4j.ready()
    mysql_ready, mysql_detail = _mysql_ready()
    minio_ready, minio_detail = _minio_ready()

    dependencies = [
        DependencyStatus(
            name="qdrant", status="ready" if vector_ready else "unavailable", detail=vector_detail
        ),
        DependencyStatus(
            name="neo4j", status="ready" if graph_ready else "unavailable", detail=graph_detail
        ),
        DependencyStatus(
            name="mysql", status="ready" if mysql_ready else "unavailable", detail=mysql_detail
        ),
        DependencyStatus(
            name="minio", status="ready" if minio_ready else "unavailable", detail=minio_detail
        ),
    ]
    all_ready = all(dep.status == "ready" for dep in dependencies)
    return ReadinessResponse(
        status="ready" if all_ready else "not_ready",
        dependencies=dependencies,
    )

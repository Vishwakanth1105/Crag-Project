# Agentic Graph RAG — Session Handoff (2026-08-18)

> Handoff for a fresh chat. Everything needed to resume is below.

## Project location
`C:\Users\ADMIN\OneDrive\Documents\Crag Project\agentic-graph-rag\`

## What this project is
Production-grade **Agentic RAG** service combining **CRAG (Corrective RAG)** + **GraphRAG**:
- **LangGraph** state machine: validate → hybrid retrieve (Qdrant vector + Neo4j graph) → rerank (Cohere) → LLM grade → rewrite/retry or **Tavily web-search fallback** → generate
- **FastAPI** endpoints: `/health`, `/ready`, `/query`, `/ingest`
- Docker stack: Qdrant (`:6333`) + Neo4j (`:7474`/`:7687`) + API (`:8000`)

## CURRENT DIRECTIVE — build a production-grade fullstack website
The RAG core works and is verified. The user approved a **7-phase fullstack expansion**:

| Phase | What |
|---|---|
| 1 | MySQL 8.4 + MinIO in compose; SQLAlchemy/Alembic; 7 tables; config vars |
| 2 | Auth: register/login/logout/me, argon2, DB-backed HTTP-only cookie sessions, CSRF; `app.cli create-admin` |
| 3 | `POST /api/v1/documents/upload` (multipart→MinIO) + background ingestion job → Qdrant/Neo4j; doc list/get/delete with cascades; **flash-lite triple extraction** |
| 4 | Conversations/messages APIs, chat persistence through `run_agent`, **flash-lite batch grading**, `query_logs` |
| 5 | Admin APIs (users/documents/ingestions/system); **remove legacy `/query` + `/ingest`** |
| 6 | `frontend/` React+Vite+TS (landing, login/register, dashboard, chat, documents, system, profile) |
| 7 | Nginx single-domain deploy; hardened headers; full compose (`frontend`, `api`, `mysql`, `qdrant`, `neo4j`, `minio`) |

### User's final product decisions (locked)
1. Stack: **React + TypeScript + Vite** frontend; **Python + FastAPI** backend; **MySQL 8.4** app DB (Qdrant=vectors, Neo4j=graph); S3-compatible storage via **MinIO**; production single-domain website.
2. **Multi-user** with self-registration; roles `user` + `admin`.
3. Auth: **HTTP-only cookie sessions** (DB-backed) + CSRF. NOT localStorage JWT. Password hashing with argon2.
4. Balanced **website**, not a chat-only app.
5. **Gemini quota optimizations folded in**: `EVALUATION_MODEL` (flash-lite) for grading + triple extraction; batch grading.
6. **Remove legacy** `/query` and `/ingest`; replaced by `POST /api/v1/conversations/{id}/messages` and `POST /api/v1/documents/upload`. `run_agent` core stays, wrapped by conversations service.
7. **Admin via CLI**: `python -m app.cli create-admin --email ... --password ...` (NOT .env bootstrap).

### Assumptions (user did not object)
- Single uvicorn worker + in-process background tasks for ingestion v1 (Celery later).
- MinIO with easy R2/AWS swap (boto3).
- API under `/api/v1`; `/docs` stays.
- Quality gates after every phase: `pytest`, `ruff check`, `ruff format --check`, `mypy src`, `compileall`.

## Provider architecture
| Layer | Provider | Config key | Model |
|---|---|---|---|
| Embeddings | **Gemini** | `GEMINI_API_KEY` (set) | `models/gemini-embedding-001` (768-dim) |
| Generation | **Gemini** | `GEMINI_API_KEY` | `gemini-3.6-flash` |
| Grading / triple extraction | **Gemini** | `GEMINI_API_KEY` | `gemini-3.6-flash` TODAY → move to `EVALUATION_MODEL` flash-lite (Phase 3/4) |
| Rerank | **Cohere** | `COHERE_API_KEY` (set) | `rerank-english-v3.0` |
| Web search (optional) | Tavily | `TAVILY_API_KEY` (EMPTY) | n/a |

`GEMINI_API_KEY` and `COHERE_API_KEY` are **both filled** in `.env`. `TAVILY_API_KEY` empty = web-search branch skips gracefully.

## Known caveat — Gemini free-tier quota (important)
- ~20 `generateContent` calls/day PER MODEL; resets midnight PT. `RERANK_TOP_K=3` set to reduce per-query calls (~4/query).
- Splitting grading/extraction onto flash-lite (separate bucket) roughly doubles daily budget — this is why EVALUATION_MODEL is Phase 3/4.

## Quality gates (all green; keep green)
```powershell
.venv\Scripts\python.exe -m pytest          # 6 tests currently
.venv\Scripts\python.exe -m ruff check src tests
.venv\Scripts\python.exe -m ruff format --check src tests
.venv\Scripts\python.exe -m mypy src
.venv\Scripts\python.exe -m compileall -q src
docker compose config
```

## Key recent fixes (do not regress)
- `qdrant.search` removed in qdrant-client 1.19 → **`query_points()`** in `src/pipeline/retrievers.py`.
- Qdrant rejects non-UUID IDs → `_as_point_id()` UUID conversion in `src/ingestion/qdrant_indexer.py`.
- mypy fixed: `SecretStr(api_key)` (embeddings), `cast()` around `with_structured_output`, `Literal["yes","no"]`, `CompiledStateGraph` + `# type: ignore[call-overload]` in `graph.py`.
- `_extract_response_text()` in `src/agents/nodes.py` (raw content-parts dict leak).
- Rerank auto-fallback: `CohereReranker` if `COHERE_API_KEY` else `PassthroughReranker` in `NodeDependencies`.
- Root `/` → 307 redirect to `/docs` in `src/api/app.py`.

## Key files
- `src/api/app.py` — FastAPI app; `/health`, `/ready`, `/query`, `/ingest`; CORS `*` (tighten in Phase 5/7).
- `src/schemas.py` — `QueryRequest/Response`, `IngestRequest/Response`, `HealthResponse`, `ReadinessResponse`, `SourceReference`, `DependencyStatus`.
- `src/config.py` — `Settings` (pydantic-settings, env_file `.env`), `require_gemini/cohere/tavily`.
- `src/agents/nodes.py`, `src/agents/graph.py` — LangGraph CRAG; `run_agent`.
- `src/pipeline/retrievers.py`, `evaluator.py`, `reranker.py` — hybrid retrieval + grading.
- `src/ingestion/parser.py`, `qdrant_indexer.py`, `neo4j_indexer.py` — parse + index; Qdrant payload already carries `document_id`.
- `src/exceptions.py` — `AppError` hierarchy.
- `docker-compose.yml`, `Dockerfile`, `.env`, `.env.example`, `requirements.txt`, `pyproject.toml`, `tests/`.

## Quick commands
```powershell
# offline tests/lint
.venv\Scripts\python.exe -m pytest
.venv\Scripts\python.exe -m ruff check src tests

# run full stack (Docker Desktop must be running)
docker compose up -d --build
docker compose ps
```
- venv: `agentic-graph-rag\.venv` (Python 3.11.9; langgraph 1.2.10, langchain-google-genai 4.3.4, qdrant-client 1.19).
- Docker Desktop may need starting: `Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"`.
- **Don't paste API keys in chat** — edit `.env` directly.
- Qdrant client-vs-server version warning (client 1.19 vs server 1.10.1) is harmless.
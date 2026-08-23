# Agentic Graph RAG

A full-stack, multi-user agentic RAG platform combining **Corrective RAG
(CRAG)** and **GraphRAG** using LangGraph, Qdrant, Neo4j, Cohere, Tavily,
FastAPI, and a React + TypeScript web UI.

## Features

- **Document ingestion** — upload PDF / TXT / Markdown; a background worker
  parses, embeds into Qdrant (parent-child chunks), and indexes triples into
  Neo4j.
- **Corrective RAG pipeline** — hybrid retrieval (vector + graph), Cohere
  reranking, LLM relevance grading with rewrite + Tavily web-search fallback,
  and grounded answers with confidence scores and sources.
- **Multi-user auth** — DB-backed sessions, argon2 password hashing, and CSRF
  double-submit protection.
- **Conversations** — persistent per-user chat history.
- **Admin console** — user/document/job statistics and dependency health.
- **Web UI** — React + TypeScript + Vite, served by nginx with SPA fallback.

## Architecture

```
        ┌──────────────────────────┐   ┌──────────────────────────┐
        │         frontend         │   │          worker          │
        │  nginx (SPA + /api proxy)│   │  python -m src.worker    │
        └───────────┬──────────────┘   └───────────┬──────────────┘
                    │ /api/v1/*                    │ poll queued jobs
        ┌───────────▼──────────────┐   ┌───────────▼──────────────┐
        │           api            │   │       ingest → index      │
        │  FastAPI + Alembic       │──▶│  Qdrant (vectors)         │
        └───┬───────┬───────┬──────┘   │  Neo4j (graph)            │
            │       │       │          └───────────┬──────────────┘
        ┌───▼───┐ ┌─▼─────┐ ┌▼────────┐   ┌────────▼──────────┐
        │ mysql │ │ minio │ │ qdrant  │   │       neo4j       │
        └───────┘ └───────┘ └─────────┘   └───────────────────┘
```

- **Application DB**: MySQL 8.4 (users, sessions, documents, ingestion jobs,
  conversations, messages, query logs), managed with Alembic.
- **Object storage**: MinIO (S3-compatible) holds uploaded files.
- **Vector store**: Qdrant (parent-child chunk indexing).
- **Graph store**: Neo4j (structured triplet extraction with `MERGE`).
- **Reranking**: Cohere Rerank v3 with a `PassthroughReranker` fallback.
- **Grading**: LLM document relevance grading (flash-lite model) with a
  deterministic `HeuristicEvaluator` fallback.
- **Web correction**: Tavily search injected when retrieval evidence is weak.
- **Orchestration**: LangGraph state machine.

## Project layout

```
agentic-graph-rag/
├── src/
│   ├── agents/          # LangGraph state, nodes, graph assembly
│   ├── api/             # FastAPI app + routers (auth, documents, …)
│   ├── auth/            # Sessions, CSRF, password hashing, dependencies
│   ├── db/              # SQLAlchemy models + session factory
│   ├── ingestion/       # Parser, Qdrant indexer, Neo4j indexer
│   ├── pipeline/        # Retrievers, reranker, evaluator
│   ├── storage/         # MinIO client
│   ├── services/        # Conversation / agent orchestration
│   ├── config.py        # Environment-driven settings
│   ├── cli.py           # Admin tooling (create-admin)
│   ├── worker.py        # Background ingestion worker
│   └── entrypoint.sh    # Wait for MySQL, run migrations, exec CMD
├── frontend/            # React + TypeScript + Vite UI (nginx-served)
├── migrations/          # Alembic revisions
├── tests/               # Offline test suite (no keys / no services)
├── docker-compose.yml   # qdrant, neo4j, mysql, minio, ollama, api, worker, frontend
├── Dockerfile
├── .env.example         # Copy to .env and fill in secrets
└── requirements.txt
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
copy .env.example .env          # then fill in API keys
```

`LLM_PROVIDER=local` (default) runs the entire pipeline offline: answers and
knowledge-graph extraction use Ollama (`OLLAMA_MODEL`, default `gemma2:2b`,
~1.7 GB RAM), embeddings use sentence-transformers
(`LOCAL_EMBEDDING_MODEL`, default `BAAI/bge-base-en-v1.5`), and relevance
grading is a deterministic heuristic — no API keys, no quota, no cost.
Set `LLM_PROVIDER=gemini` to use Google AI for generation/embeddings/grading
instead (`GEMINI_API_KEY`). `COHERE_API_KEY` enables reranking (a pass-through
fallback is used without it). `TAVILY_API_KEY` enables web-search correction
(a deterministic fallback is used without it). The API starts regardless of
which keys are present.

> After switching embedding models, re-upload existing documents so their
> vectors match the active model's vector space.

## Run with Docker

```bash
docker compose up --build
```

This starts (all healthy-gated):

| Service   | Port(s)                    | Purpose                          |
| --------- | -------------------------- | -------------------------------- |
| frontend  | `:8080`                    | Web UI (nginx + SPA fallback)    |
| api       | `:8000`                    | FastAPI backend                  |
| worker    | —                          | Background ingestion             |
| ollama    | internal `:11434`          | Local LLM inference (gemma2:2b)  |
| mysql     | `:3307` (host)             | Application database             |
| minio     | `:9000` / `:9001` (console) | Object storage                  |
| qdrant    | `:6333`                    | Vector store                     |
| neo4j     | `:7474` / `:7687`          | Graph store                      |

The first start pulls the Ollama model (~1.6 GB download, then cached in the
`ollama_data` volume); the HuggingFace embedding model is cached in `hf_cache`.

Host port `3306` is avoided because a local `mysqld` commonly occupies it.

Create an admin account:

```bash
docker compose exec api python -m src.cli create-admin --email admin@example.com --password change-me
```

## Web UI

- Open http://localhost:8080, register, and log in.
- **Documents** uploads files; **Chat** asks grounded questions; **System**
  (admin only) shows statistics and dependency health.
- For local UI development with hot reload:

  ```bash
  cd frontend
  npm install
  npm run dev        # http://localhost:5173, proxies /api to :8000
  ```

## Run the tests

Tests are fully offline — no API keys, no Docker, no Qdrant/Neo4j:

```bash
pytest
ruff check src tests
ruff format --check src tests
mypy src
```

## API

All data endpoints live under `/api/v1` and are guarded by session auth + CSRF
(double-submit cookie/header). Flow: `GET /api/v1/auth/csrf` first, then send
the `X-CSRF-Token` header on state-changing requests.

| Method | Path                                 | Description                          |
| ------ | ------------------------------------ | ------------------------------------ |
| GET    | `/health`                            | Liveness check.                      |
| GET    | `/ready`                             | Readiness (Qdrant/Neo4j/MySQL/MinIO).|
| GET    | `/api/v1/auth/csrf`                  | CSRF token + cookie.                 |
| POST   | `/api/v1/auth/register`              | Register a user.                     |
| POST   | `/api/v1/auth/login`                 | Log in (sets session cookie).        |
| POST   | `/api/v1/auth/logout`                | Log out.                             |
| GET    | `/api/v1/auth/me`                    | Current user.                        |
| POST   | `/api/v1/documents/upload`           | Upload a document (multipart).       |
| GET    | `/api/v1/documents`                  | List own documents.                  |
| GET    | `/api/v1/documents/{id}`             | Document + ingestion status.         |
| DELETE | `/api/v1/documents/{id}`             | Delete document (cascades to stores).|
| GET    | `/api/v1/conversations`              | List own conversations.              |
| POST   | `/api/v1/conversations`              | Create a conversation.               |
| DELETE | `/api/v1/conversations/{id}`         | Delete a conversation.               |
| GET    | `/api/v1/conversations/{id}/messages`| List messages.                       |
| POST   | `/api/v1/conversations/{id}/messages`| Ask a question (runs the pipeline).  |
| GET    | `/api/v1/admin/users`                | Admin: list users.                   |
| GET    | `/api/v1/admin/documents`            | Admin: list documents.               |
| GET    | `/api/v1/admin/ingestions`           | Admin: list ingestion jobs.          |
| GET    | `/api/v1/admin/system`               | Admin: counts + dependency health.   |
# Agentic Graph RAG

[![CI](https://github.com/Vishwakanth1105/Crag-Project/actions/workflows/ci.yml/badge.svg)](https://github.com/Vishwakanth1105/Crag-Project/actions/workflows/ci.yml)

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
- **Multi-user auth** — DB-backed sessions (default 8-hour expiry via
  `SESSION_TTL_HOURS`), argon2 password hashing, and CSRF double-submit
  protection.
- **Password reset** — "Forgot password?" flow emails a single-use reset link
  (60-minute expiry); resetting revokes all existing sessions. Emails are sent
  through the Brevo API when `BREVO_API_KEY` is configured, otherwise logged
  to the api container output.
- **Conversations** — persistent per-user chat history.
- **Support tickets** — every user can open support threads; admins get an
  inbox with open / pending / resolved filters, replies (live polling), and a
  resolve/reopen lifecycle.
- **Admin console** — platform dashboard with usage statistics and dependency
  health; user management with per-user activity detail, ban/unban (kills
  sessions instantly), and full deletion that cascades to MinIO blobs, Qdrant
  chunks, and Neo4j nodes. Admin navigation replaces the end-user workspace
  (Chat/Documents) with management tools.
- **Web UI** — React + TypeScript + Vite, served by nginx with SPA fallback.
- **CI** — GitHub Actions runs pytest, ruff, mypy, and the frontend
  lint/typecheck/build on every push.

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
  conversations, messages, query logs, password-reset tokens, support
  threads), managed with Alembic.
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

Other optional settings:

| Variable            | Default                          | Purpose                                        |
| ------------------- | -------------------------------- | ---------------------------------------------- |
| `SESSION_TTL_HOURS` | `8`                              | Login session lifetime (cookie + server side). |
| `FRONTEND_URL`      | `http://localhost:5173`          | Base URL used in password-reset links.         |
| `BREVO_API_KEY`     | —                                | Brevo API key; enables real reset emails.      |
| `BREVO_FROM_EMAIL`  | —                                | Verified sender address for those emails.      |

Without `BREVO_API_KEY`, password-reset emails are printed to the api
container log (`docker compose logs api`) instead of being sent.

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
- **Documents** uploads files; **Chat** asks grounded questions; **Support**
  opens tickets to the admins; **Profile** manages the account.
- Admins get a platform console instead of the end-user workspace: usage
  stats, dependency health, **Users** (activity detail, ban/unban, delete),
  a **Support** inbox with status filters and replies, and **System**.
- "Forgot password?" on the login page emails a reset link (requires
  `BREVO_API_KEY`; otherwise the link is logged to `docker compose logs api`).
- For local UI development with hot reload:

  ```bash
  cd frontend
  npm install
  npm run dev        # http://localhost:5173, proxies /api to :8000
  ```

## Run the tests

Tests are fully offline — no API keys, no Docker, no Qdrant/Neo4j. The same
gates run automatically on every push via GitHub Actions (`.github/workflows/ci.yml`):

```bash
pytest
ruff check src tests
ruff format --check src tests
mypy src

cd frontend && npm ci && npm run lint && npm run build
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
| POST   | `/api/v1/auth/forgot-password`       | Email a single-use reset link.       |
| POST   | `/api/v1/auth/reset-password`        | Consume reset token, set password.   |
| POST   | `/api/v1/documents/upload`           | Upload a document (multipart).       |
| GET    | `/api/v1/documents`                  | List own documents.                  |
| GET    | `/api/v1/documents/{id}`             | Document + ingestion status.         |
| DELETE | `/api/v1/documents/{id}`             | Delete document (cascades to stores).|
| GET    | `/api/v1/conversations`              | List own conversations.              |
| POST   | `/api/v1/conversations`              | Create a conversation.               |
| DELETE | `/api/v1/conversations/{id}`         | Delete a conversation.               |
| GET    | `/api/v1/conversations/{id}/messages`| List messages.                       |
| POST   | `/api/v1/conversations/{id}/messages`| Ask a question (runs the pipeline).  |
| POST   | `/api/v1/support`                    | Open a support ticket.               |
| GET    | `/api/v1/support/mine`               | List own tickets.                    |
| GET    | `/api/v1/support/{id}`               | Ticket thread (owner or admin).      |
| POST   | `/api/v1/support/{id}/messages`      | Reply (reopens resolved tickets).    |
| GET    | `/api/v1/support/admin/threads`      | Admin: all tickets (?status= filter).|
| PATCH  | `/api/v1/support/admin/{id}/status`  | Admin: open / pending / resolved.    |
| GET    | `/api/v1/admin/users`                | Admin: list users.                   |
| GET    | `/api/v1/admin/users/{id}`           | Admin: user detail + activity.       |
| PATCH  | `/api/v1/admin/users/{id}/status`    | Admin: ban / unban (revokes sessions).|
| DELETE | `/api/v1/admin/users/{id}`           | Admin: delete user + all their data. |
| GET    | `/api/v1/admin/documents`            | Admin: list documents.               |
| GET    | `/api/v1/admin/ingestions`           | Admin: list ingestion jobs.          |
| GET    | `/api/v1/admin/system`               | Admin: counts + dependency health.   |
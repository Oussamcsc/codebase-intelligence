<div align="center">

# Codebase Intelligence

### AI-powered repository analysis and senior-review assistant

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://react.dev/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://docs.docker.com/compose/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Quick Start](#quick-start) · [Architecture](#architecture) · [Configuration](#configuration) · [API](#api-surface) · [Troubleshooting](#troubleshooting)

</div>

---

## Project snapshot

Codebase Intelligence is a full-stack developer tool for understanding repositories and producing grounded AI-assisted code review. It combines static analysis, dependency/call-graph inspection, duplicate and type-signal detection, optional retrieval-augmented review context, and OpenAI review synthesis to identify the issues a senior engineer should inspect first.

It is built to answer practical engineering questions:

- Which files, functions, or dependencies are risky?
- Where are maintainability, correctness, performance, or security problems likely hiding?
- Which findings are backed by static-analysis evidence instead of generic LLM advice?
- How can a repository review be shared, exported, and revisited later?

---

## Core capabilities

- **GitHub repository ingestion** from public repository URLs.
- **AST/static analysis** for structure, complexity, suspicious patterns, and file/function metadata.
- **Dependency and impact analysis** through custom graph inspection.
- **Duplicate-code detection** with concrete file-level references.
- **Type-signal analysis** with optional mypy-oriented checks.
- **Configurable review modes** for latency control: fast mode by default, detailed mode when deeper review is worth the extra cost.
- **Noise filtering and severity calibration** to suppress low-value review comments and prioritize actionable issues.
- **Optional RAG context** backed by ChromaDB and OpenAI embeddings.
- **Persistent analysis jobs** using SQLite for job status and results.
- **FastAPI backend + React frontend** with WebSocket progress updates, result sharing, and JSON export.
- **Containerized local stack** with Docker Compose for repeatable setup.

---

## Quick start

### Option 1: Docker Setup — recommended

This is the primary setup path. It starts the complete local ecosystem:

- FastAPI API server on <http://localhost:8000>
- React web UI served by Nginx on <http://localhost:3000>
- ChromaDB sidecar on <http://localhost:8001>
- Persistent Docker volumes for SQLite analysis results and Chroma data
- A private Docker network connecting the services

#### Prerequisites

- Docker Desktop or Docker Engine with Docker Compose v2
- A valid OpenAI API key
- GitHub OAuth credentials only if you want authenticated GitHub browsing; manual public repo URL analysis works without OAuth.

#### 1. Clone the repository

```bash
git clone https://github.com/Oussamcsc/codebase-intelligence.git
cd codebase-intelligence
```

#### 2. Create your environment file

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```env
OPENAI_API_KEY=your-openai-api-key-here
```

Optional GitHub OAuth configuration:

```env
GITHUB_CLIENT_ID=your-github-client-id-here
GITHUB_CLIENT_SECRET=your-github-client-secret-here
```

For local OAuth, configure your GitHub OAuth App with:

- Homepage URL: `http://localhost:3000`
- Authorization callback URL: `http://localhost:8000/auth/github/callback`

#### 3. Start the stack

```bash
docker compose up --build
```

Open <http://localhost:3000>.

Useful checks:

```bash
curl http://localhost:8000/health
curl http://localhost:8001/api/v1/heartbeat
```

#### 4. Stop or reset the stack

Stop containers while keeping persisted data:

```bash
docker compose down
```

Remove containers and local Docker volumes:

```bash
docker compose down -v
```

---

### Option 2: Local development without Docker

Use this only when you are actively developing outside containers.

Prerequisites:

- Python 3.11+
- Node.js 18+
- OpenAI API key

Backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and set OPENAI_API_KEY.

uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

Frontend, in a second terminal:

```bash
cd web
npm install
npm start
```

Open <http://localhost:3000>.

If your Python installation cannot create or seed virtual environments, `uv` works well:

```bash
uv python install 3.11
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

---

## Architecture

```text
┌──────────────────────────────────────────────────────────────────┐
│                    Codebase Intelligence                          │
└──────────────────────────────────────────────────────────────────┘

        Browser
          │
          ▼
┌──────────────────┐        HTTP / WebSocket        ┌──────────────────┐
│ React + Nginx    │ ─────────────────────────────► │ FastAPI API       │
│ localhost:3000   │ ◄───────────────────────────── │ localhost:8000    │
└──────────────────┘                                └───────┬──────────┘
                                                            │
                         ┌──────────────────────────────────┼──────────────────────────────────┐
                         │                                  │                                  │
                         ▼                                  ▼                                  ▼
              ┌──────────────────┐              ┌──────────────────┐              ┌──────────────────┐
              │ OpenAI APIs      │              │ ChromaDB Sidecar │              │ SQLite Volume    │
              │ review + embed   │              │ localhost:8001   │              │ /app/data/*.db   │
              └──────────────────┘              └──────────────────┘              └──────────────────┘
```

### Runtime flow

1. **Repository clone** — the API clones a public GitHub repository into a temporary workspace.
2. **File discovery** — files are filtered by pattern and `MAX_ANALYSIS_FILES` for latency control.
3. **Static analysis** — analyzers inspect AST structure, dependency/call graph signals, type hints, duplicate code, and suspicious patterns.
4. **Quality filtering** — generic noise is suppressed or downgraded so output emphasizes actionable risks.
5. **Optional RAG lookup** — when `ENABLE_RAG=true`, the API retrieves review context from ChromaDB using OpenAI embeddings.
6. **Review synthesis** — OpenAI produces a structured review from analyzer evidence, configured by `ANALYSIS_MODE`, `GPT_REVIEW_MODEL`, and timeout settings.
7. **Persistence and streaming** — SQLite stores job state/results while WebSocket progress updates stream to the frontend.

### Recent performance and quality optimizations

- **Fast mode by default**: `ANALYSIS_MODE=fast` and `GPT_REVIEW_MODEL=gpt-4o-mini` reduce local latency and cost for normal repository checks.
- **Configurable depth**: `analysis_mode` can be set per request, and defaults can be changed through environment variables.
- **File-count guardrails**: `MAX_ANALYSIS_FILES` protects local runs from accidentally analyzing very large repositories.
- **Optional RAG startup**: `ENABLE_RAG=false` by default keeps the API responsive even before the Chroma knowledge base is needed.
- **Lazy reviewer initialization**: health/config endpoints remain available even when credentials are missing, while analysis endpoints clearly report missing `OPENAI_API_KEY`.
- **Persistent container paths**: Docker stores SQLite and Chroma data under named volumes, avoiding accidental loss across container restarts.
- **Hardened OAuth config**: callback and frontend redirects derive from `BACKEND_URL` and `FRONTEND_URL`, reducing redirect mismatch bugs.

---

## Configuration

`.env.example` is the source template for local Docker and non-Docker runs.

| Variable | Default | Purpose |
|---|---:|---|
| `OPENAI_API_KEY` | placeholder | Required for analysis and OpenAI review synthesis. |
| `GITHUB_CLIENT_ID` | empty/placeholder | Optional GitHub OAuth app client ID. |
| `GITHUB_CLIENT_SECRET` | empty/placeholder | Optional GitHub OAuth app secret. |
| `BACKEND_URL` | `http://localhost:8000` | Public URL used for API links and OAuth callback construction. |
| `FRONTEND_URL` | `http://localhost:3000` | Public web UI URL used for redirects. |
| `REACT_APP_API_URL` | `http://localhost:8000` | API URL baked into the frontend Docker build. |
| `API_HOST` | `0.0.0.0` | API bind host inside the container/process. |
| `API_PORT` | `8000` | API bind port inside the container/process. |
| `DB_PATH` | `/app/data/code_review_results.db` | SQLite results database path in Docker. |
| `VECTOR_DB_PATH` | `/app/data/chroma_db` | Local embedded Chroma path for non-sidecar fallback/dev use. |
| `CHROMA_HOST` | `chroma` | Chroma sidecar hostname on the Docker network. |
| `CHROMA_PORT` | `8000` | Chroma sidecar internal port. Host maps this to `8001`. |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model for optional RAG. |
| `ANALYSIS_MODE` | `fast` | Default reviewer mode: `fast` or `detailed`. |
| `GPT_REVIEW_MODEL` | `gpt-4o-mini` | Default OpenAI chat model for review synthesis. |
| `GPT_TIMEOUT_SECONDS` | `30` | Timeout budget for review synthesis. |
| `MAX_ANALYSIS_FILES` | `40` | Default maximum files analyzed per GitHub job. |
| `ENABLE_RAG` | `false` | Enables Chroma-backed RAG context when set to `true`. |
| `CHROMA_SERVER_HOST` | `0.0.0.0` | Chroma container bind host. |
| `CHROMA_SERVER_HTTP_PORT` | `8000` | Chroma container internal HTTP port. |
| `CHROMA_HOST_PORT` | `8001` | Host port exposed for Chroma debugging. |

Never commit `.env`, generated SQLite files, Chroma data, virtual environments, dependency folders, or build outputs.

---

## Docker Compose services

| Service | Container | Host port | Description |
|---|---|---:|---|
| `api` | `codebase-intelligence-api` | `8000` | FastAPI backend, analysis engine, SQLite persistence. |
| `web` | `codebase-intelligence-web` | `3000` | Production React build served by Nginx. |
| `chroma` | `codebase-intelligence-chroma` | `8001` | ChromaDB sidecar for optional RAG collections. |

Named volumes:

- `codebase-intelligence-api-data` → `/app/data`
- `codebase-intelligence-chroma-data` → `/chroma/chroma`

Network:

- `codebase-intelligence-net` private bridge network

---

## API surface

### Analysis

- `POST /github/analyze` — start repository analysis.
- `GET /github/status/{job_id}` — check analysis status.
- `GET /github/results/{job_id}` — fetch completed results.
- `GET /github/share/{job_id}` — public/shareable result endpoint.
- `GET /github/export/{job_id}/json` — export results as JSON.
- `WS /ws/progress/{job_id}` — stream progress updates.

Example request:

```json
{
  "repo_url": "https://github.com/user/repo",
  "branch": "main",
  "files_pattern": "*.py",
  "max_files": 40,
  "analysis_mode": "fast"
}
```

### Review utilities

- `POST /review` — review a code string.
- `POST /review-file` — review a file path available to the backend.
- `POST /upload-review` — upload and review a file.
- `GET /stats` — system stats.
- `GET /health` — health check.

### Authentication

- `GET /auth/github` — start GitHub OAuth flow.
- `GET /auth/github/callback` — OAuth callback handler.

---

## Development checks

```bash
python3 -m py_compile config.py api.py Code_reviewer.py Codebase_analyzer.py pattern_matcher.py type_analyzer.py duplicate_detector.py cli.py scan_project.py
pytest

cd web
npm run build
```

Docker checks:

```bash
docker compose config
docker compose up --build
```

---

## Troubleshooting

**API container starts, but analysis returns 503**

- Set `OPENAI_API_KEY` in `.env`.
- Recreate the API container after changing `.env`: `docker compose up --build api`.

**Frontend cannot reach the backend**

- Confirm the API health check: `curl http://localhost:8000/health`.
- Confirm `REACT_APP_API_URL=http://localhost:8000` before building the web image.
- Rebuild the web container if the frontend API URL changes.

**GitHub OAuth fails with a redirect mismatch**

- GitHub callback must exactly match `http://localhost:8000/auth/github/callback`.
- `BACKEND_URL` should be `http://localhost:8000` for local Docker.
- `FRONTEND_URL` should be `http://localhost:3000` for local Docker.

**ChromaDB is unavailable**

- Confirm the sidecar is running: `docker compose ps chroma`.
- Check Chroma directly: `curl http://localhost:8001/api/v1/heartbeat`.
- If `ENABLE_RAG=false`, analysis can still run without Chroma-backed RAG.

**Large repository analysis is slow**

- Keep `ANALYSIS_MODE=fast` for local runs.
- Lower `MAX_ANALYSIS_FILES` or use a narrower `files_pattern` such as `*.py`.
- Switch to `analysis_mode=detailed` only for focused follow-up reviews.

---

## License

MIT — see [LICENSE](LICENSE).

---

<div align="center">

[⬆ Back to Top](#codebase-intelligence)

</div>

<div align="center">

# Code Intel

### AI-powered codebase analysis and review platform

[![Live Demo](https://img.shields.io/badge/demo-live-success)](https://codebase-intelligence.vercel.app)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://react.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Live Demo](https://codebase-intelligence.vercel.app) · [Local Setup](LOCAL_SETUP.md) · [Quick Start](#quick-start) · [Architecture](#architecture) · [API](#api-surface)

</div>

---

## Project snapshot

Code Intel is a portfolio-grade developer tool for repository understanding and AI-assisted code review. It combines Python static analysis, dependency/call-graph inspection, lightweight retrieval, and OpenAI review synthesis to produce practical engineering feedback with concrete code references.

It is designed to answer questions like:

- Which files or functions are risky?
- Are there dependency or maintainability problems?
- Where is duplicate or suspicious code hiding?
- What correctness, stability, performance, or security issues should a reviewer inspect first?
- Can AI review output be grounded in static-analysis evidence instead of generic advice?

---

## Core capabilities

- **Repository ingestion** from public GitHub URLs
- **AST/static analysis** for structural code understanding
- **Dependency and impact analysis** through custom graph inspection
- **Duplicate code and pattern detection** with file-level references
- **Type-signal analysis** with optional mypy support
- **Lightweight RAG context** using ChromaDB for reusable best-practice/common-issue guidance
- **OpenAI review synthesis** for senior-engineer-style recommendations
- **FastAPI backend** with React frontend and WebSocket progress updates

---

## Tech stack

| Layer | Tools |
|---|---|
| Backend | Python, FastAPI, Uvicorn, Pydantic |
| Analysis | Python AST, custom analyzers, dependency/call graph inspection, duplicate detection, optional mypy |
| Retrieval | ChromaDB, OpenAI embeddings |
| AI | OpenAI chat completions for review synthesis |
| Persistence | Local SQLite for analysis job status/results |
| Frontend | React 18, Axios, React Router, WebSocket progress, syntax/JSON viewers |
| Infra | Docker, Docker Compose, python-dotenv, GitHub clone flow |

---

## Quick start

For the shortest reliable boot path on a new machine, follow [`LOCAL_SETUP.md`](LOCAL_SETUP.md).

### Prerequisites

- Python 3.11+
- Node.js 18+
- A valid OpenAI API key
- GitHub OAuth credentials only if you want OAuth repo browsing; manual public repo URL analysis works without OAuth.

### Backend

```bash
git clone https://github.com/Oussamcsc/codebase-intelligence.git
cd codebase-intelligence

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env and set OPENAI_API_KEY at minimum.

uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

In a second terminal:

```bash
cd web
npm install
npm start
```

Then open <http://localhost:3000>.

---

## Environment variables

```env
OPENAI_API_KEY=replace-with-openai-key
GITHUB_CLIENT_ID=replace-with-github-client-id
GITHUB_CLIENT_SECRET=replace-with-github-client-secret
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
API_HOST=0.0.0.0
API_PORT=8000
DB_PATH=code_review_results.db
VECTOR_DB_PATH=./chroma_db
EMBEDDING_MODEL=text-embedding-3-small
```

Never commit `.env` files, generated SQLite databases, `chroma_db/`, or dependency folders.

---

## GitHub OAuth setup

OAuth is optional for local manual URL analysis. If you want authenticated repo browsing:

1. Go to [GitHub Developer Settings](https://github.com/settings/developers).
2. Create a new OAuth App.
3. Use:
   - Homepage URL: `http://localhost:3000`
   - Authorization callback URL: `http://localhost:8000/auth/github/callback`
4. Add the generated credentials to `.env`:

```env
GITHUB_CLIENT_ID=your_client_id_here
GITHUB_CLIENT_SECRET=your_client_secret_here
```

Restart the backend after changing `.env`.

---

## Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                         Code Intel                            │
└──────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
         ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
         │  React  │    │ FastAPI │    │ GitHub  │
         │   Web   │◄──►│   API   │◄──►│  Repos  │
         │  (3000) │ WS │  (8000) │    │         │
         └─────────┘    └────┬────┘    └─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
         ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
         │ OpenAI  │   │ ChromaDB│   │ SQLite  │
         │  LLM +  │   │ Review  │   │ Jobs +  │
         │Embeddings│  │ Context │   │ Results │
         └─────────┘   └─────────┘   └─────────┘
```

### Analysis pipeline

1. **Repository clone** — clone a public GitHub repository into a temporary directory.
2. **File discovery** — select files matching the requested pattern.
3. **AST/static analysis** — inspect structure, patterns, duplicate code, and type signals.
4. **Dependency graph analysis** — build graph context for function/file relationships.
5. **RAG context lookup** — retrieve relevant best-practice/common-issue guidance from ChromaDB.
6. **OpenAI review synthesis** — combine evidence into a structured review with exact references.
7. **Persistence and streaming** — store job state/results in SQLite and stream progress over WebSocket.

---

## API surface

### Analysis

- `POST /github/analyze` — start repository analysis
- `GET /github/status/{job_id}` — check analysis status
- `GET /github/results/{job_id}` — fetch completed results
- `GET /github/share/{job_id}` — public/shareable result endpoint
- `GET /github/export/{job_id}/json` — export results as JSON
- `WS /ws/progress/{job_id}` — stream live progress updates

Example request:

```json
{
  "repo_url": "https://github.com/user/repo",
  "branch": "main",
  "files_pattern": "*.py"
}
```

### Review utilities

- `POST /review` — review a code string
- `POST /review-file` — review a file path available to the backend
- `POST /upload-review` — upload and review a file
- `GET /stats` — system stats
- `GET /health` — health check

### Authentication

- `GET /auth/github` — start GitHub OAuth flow
- `GET /auth/github/callback` — OAuth callback handler

---

## Troubleshooting

**Backend fails at startup**
- Confirm `.env` exists.
- Confirm `OPENAI_API_KEY` is set and valid.
- Run from the repository root.

**Frontend cannot reach backend**
- Backend should be running at <http://localhost:8000>.
- Frontend defaults to `http://localhost:8000` unless `REACT_APP_API_URL` is set.

**GitHub OAuth fails locally**
- Verify callback URL: `http://localhost:8000/auth/github/callback`.
- Verify `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` are set.
- Manual public repo URL analysis can still work without OAuth.

**Large repository analysis is slow**
- Start with `*.py` or another narrow file pattern.
- Large repos can take several minutes depending on file count and OpenAI latency.

---

## Development checks

```bash
python3 -m py_compile config.py api.py Code_reviewer.py Codebase_analyzer.py pattern_matcher.py type_analyzer.py duplicate_detector.py cli.py scan_project.py
pytest

cd web
npm run build
```

---

## License

MIT — see [LICENSE](LICENSE).

---

<div align="center">

[⬆ Back to Top](#code-intel)

</div>

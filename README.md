<div align="center">

# Code Intel

### AI-powered codebase analysis and review platform

[![Live Demo](https://img.shields.io/badge/demo-live-success)](https://codebase-intelligence.vercel.app)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://react.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Live Demo](https://codebase-intelligence.vercel.app) · [Quick Start](#quick-start) · [Architecture](#architecture) · [API](#api-surface)

</div>

---

## Project snapshot

Code Intel is a portfolio-grade developer tool focused on repository understanding and AI-assisted code review. It demonstrates backend architecture, static analysis, graph algorithms, retrieval-augmented generation, LLM orchestration, and a deployed full-stack user experience.

It is designed to answer practical engineering questions:

- Where are the risky files?
- Are there circular dependencies?
- Are there repeated code patterns?
- What security, performance, or architecture issues should a reviewer inspect first?
- Can AI review output include concrete file/line context instead of generic advice?

---

## Core capabilities

- **Repository ingestion** from GitHub URLs
- **AST/static analysis** for structural code understanding
- **Circular dependency detection** using directed graph traversal
- **Duplicate code and pattern detection** with file-level references
- **Vector retrieval** through ChromaDB for context-aware analysis
- **LLM review agents** for security, performance, and architecture feedback
- **FastAPI backend** with a React frontend and deployed demo

---

## Tech stack

| Layer | Tools |
|---|---|
| Backend | Python, FastAPI, Pydantic |
| Analysis | AST parsing, graph traversal, custom analyzers |
| Retrieval | ChromaDB, embeddings |
| AI | OpenAI-compatible LLM workflows |
| Frontend | React |
| Infra | Docker, Vercel/Railway-style deployment config |

---

## Quick start

### Prerequisites

- Python 3.11+
- Node.js 18+
- OpenAI API key
- GitHub OAuth app credentials if using authenticated GitHub flows

### Backend

```bash
git clone https://github.com/Oussamcsc/codebase-intelligence.git
cd codebase-intelligence
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python api.py
```

### Frontend

```bash
cd web
npm install
npm start
```

Then open:

```text
http://localhost:3000
```

---

## Environment variables

```env
OPENAI_API_KEY=replace-with-openai-key
GITHUB_CLIENT_ID=replace-with-github-client-id
GITHUB_CLIENT_SECRET=replace-with-github-client-secret
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
VECTOR_DB_PATH=./chroma_db
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

Never commit `.env` files or generated vector database files.

---

## Architecture

```text
React UI
  → FastAPI backend
  → GitHub repository ingestion
  → Static/AST analyzers
  → Dependency graph builder
  → ChromaDB vector context
  → LLM review agents
  → Structured report output
```

### Analysis pipeline

1. Accept repository URL and analysis options.
2. Fetch or clone repository content.
3. Discover relevant files.
4. Run static analyzers and AST parsing.
5. Build dependency graph and detect cycles.
6. Store/retrieve contextual chunks with ChromaDB.
7. Run targeted AI review workflows.
8. Return structured results for the UI.

---

## API surface

Representative endpoints:

```http
POST /github/analyze
GET /github/status/{job_id}
GET /github/results/{job_id}
WS  /ws/progress/{job_id}
```

Example analysis request:

```json
{
  "repo_url": "https://github.com/username/repository",
  "branch": "main",
  "file_patterns": ["*.py", "*.js", "*.ts"]
}
```

---

## Project status

This is a portfolio-grade AI developer tooling project. The current version demonstrates the core analysis pipeline, deployed UI, and backend architecture. Next improvements would be stronger job persistence, richer language coverage, CI hardening, and deeper evaluation of AI review quality.

---

## License

MIT — see [LICENSE](LICENSE).

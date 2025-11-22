<div align="center">

# 🚀 Code Intel

### AI-Powered Codebase Analysis Platform

*Understand any codebase in seconds, not hours*

[![Live Demo](https://img.shields.io/badge/demo-live-success)](https://codebase-intelligence.vercel.app)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg)](https://fastapi.tiangolo.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-412991.svg)](https://openai.com/)

[Live Demo](https://codebase-intelligence.vercel.app) • [Features](#-features) • [Quick Start](#-quick-start) • [Documentation](#-documentation)

</div>

---

## 🎯 What is Code Intel?

Code Intel is an intelligent code analysis platform that combines **static analysis**, **AST parsing**, and **LLM reasoning** to help developers understand complex codebases, identify issues, and improve code quality—all in real-time.

Simply connect your GitHub repository and get:
- 🔍 **Deep code analysis** - Security vulnerabilities, performance bottlenecks, anti-patterns
- 🔄 **Circular dependency detection** - Using graph traversal algorithms
- 📊 **Code duplication tracking** - With exact file/line references
- 🤖 **AI-powered insights** - Context-aware recommendations from specialized agents
- ⚡ **Real-time results** - Stream analysis progress via WebSocket

---

## ✨ Features

### 🔌 **GitHub Integration**
One-click repository scanning directly from GitHub URLs. No manual uploads needed.

### 🧠 **Multi-Agent Analysis**
Specialized AI agents analyze different aspects:
- **Security Agent** - Identifies vulnerabilities and security risks
- **Performance Agent** - Detects bottlenecks and optimization opportunities  
- **Architecture Agent** - Reviews code structure and design patterns

### 🎨 **AST-Based Code Understanding**
Parse and analyze code structure using Abstract Syntax Trees to identify:
- Code patterns and anti-patterns
- Duplicate code blocks with exact references
- Structural issues and complexity hotspots

### 📈 **RAG Pipeline**
Vector embeddings (ChromaDB) combined with traditional static analysis for context-aware insights that understand your entire codebase.

### 🎯 **Graph Analysis**
Directed graph traversal to detect circular dependencies and visualize module relationships.

### 💾 **Export Results**
Download comprehensive analysis reports as JSON for further processing or sharing.

---

## 🛠️ Tech Stack

**Backend:**
- FastAPI (Python) - High-performance async API
- LangChain - Multi-agent orchestration
- ChromaDB - Vector database for embeddings
- OpenAI GPT-4 - LLM reasoning

**Frontend:**
- React 18 - Modern UI framework
- WebSocket - Real-time progress updates
- Glassmorphism UI - Beautiful, responsive design

**Infrastructure:**
- PostgreSQL - Data persistence
- GitHub API - Repository integration
- Vercel - Deployment

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))
- GitHub OAuth App ([Setup guide](#github-oauth-setup))

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/code-intel.git
cd code-intel
```

### 2. Backend Setup
```bash
# Install Python dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env and add your credentials
nano .env
```

**Required environment variables:**
```bash
# OpenAI API Key
OPENAI_API_KEY=sk-your-key-here

# GitHub OAuth (see setup guide below)
GITHUB_CLIENT_ID=your-client-id
GITHUB_CLIENT_SECRET=your-client-secret

# Server URLs (for local development)
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000

# Vector DB
VECTOR_DB_PATH=./chroma_db
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

### 3. Frontend Setup
```bash
# Navigate to web directory
cd web

# Install dependencies
npm install

# Start development server
npm start
```

### 4. Start the Backend
```bash
# From project root
python api.py
```

### 5. Access the App

Open [http://localhost:3000](http://localhost:3000) in your browser 🎉

---

## 🔐 GitHub OAuth Setup

To enable GitHub repository scanning, you need to create a GitHub OAuth App:

### Step 1: Create OAuth App

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click **"New OAuth App"**
3. Fill in the details:
   - **Application name:** `Code Intel (Local Dev)`
   - **Homepage URL:** `http://localhost:3000`
   - **Authorization callback URL:** `http://localhost:8000/auth/github/callback`
4. Click **"Register application"**

### Step 2: Get Credentials

1. Copy your **Client ID**
2. Click **"Generate a new client secret"** and copy it
3. Add both to your `.env` file:
```bash
GITHUB_CLIENT_ID=your_client_id_here
GITHUB_CLIENT_SECRET=your_client_secret_here
```

### Step 3: Restart Backend
```bash
# Kill the running server and restart
python api.py
```

✅ GitHub integration is now ready!

---

## 📖 Usage

### Analyze a Repository

1. **Enter Repository URL**
```
   https://github.com/username/repository
```

2. **Configure Analysis** (optional)
   - Branch: `main` (default)
   - File patterns: `*.py, *.js, *.ts` (customize as needed)

3. **Start Analysis**
   - Click "Analyze Repository"
   - Watch real-time progress via WebSocket
   - View results in interactive file explorer

4. **Review Results**
   - Expandable file tree showing all issues
   - Detailed descriptions with severity levels
   - Code snippets with exact line references
   - Export as JSON for further analysis

### Example Repositories to Try

| Repository | Language | Complexity |
|-----------|----------|-----------|
| `pallets/flask` | Python | Medium |
| `django/django` | Python | High |
| `fastapi/fastapi` | Python | Medium |
| `facebook/react` | JavaScript | High |

---

## 🏗️ Architecture
```
┌──────────────────────────────────────────────────────────────┐
│                         Code Intel                            │
└──────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
         ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
         │  React  │    │ FastAPI │    │ GitHub  │
         │   Web   │◄──►│   API   │◄──►│   API   │
         │  (3000) │ WS │  (8000) │    │         │
         └─────────┘    └────┬────┘    └─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
         ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
         │ OpenAI  │   │ ChromaDB│   │  AST    │
         │   API   │   │ Vector  │   │ Parser  │
         │  (GPT4) │   │   DB    │   │         │
         └─────────┘   └─────────┘   └─────────┘
```

### Analysis Pipeline

1. **Repository Cloning** - Clone GitHub repo to temp directory
2. **File Discovery** - Identify relevant files based on patterns
3. **AST Parsing** - Parse code structure and extract metadata
4. **Vector Embedding** - Generate embeddings and store in ChromaDB
5. **Static Analysis** - Run traditional linters and analyzers
6. **Graph Analysis** - Build dependency graph and detect cycles
7. **LLM Reasoning** - Multi-agent analysis with GPT-4
8. **Results Synthesis** - Combine insights and generate report

---

## 🎨 API Endpoints

### Analysis
- `POST /github/analyze` - Start repository analysis
```json
  {
    "repo_url": "https://github.com/user/repo",
    "branch": "main",
    "file_patterns": ["*.py"]
  }
```

### Status & Results
- `GET /github/status/{job_id}` - Check analysis status
- `GET /github/results/{job_id}` - Get analysis results
- `WS /ws/progress/{job_id}` - Real-time progress updates

### Authentication
- `GET /auth/github` - Initiate GitHub OAuth flow
- `GET /auth/github/callback` - OAuth callback handler

---

## 🐛 Troubleshooting

### Common Issues

**"GitHub OAuth not working"**
- Verify `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` are set correctly
- Check callback URL matches: `http://localhost:8000/auth/github/callback`
- Make sure backend is running on port 8000

**"OpenAI API errors"**
- Verify your `OPENAI_API_KEY` is valid
- Check you have API credits remaining
- Ensure you're using GPT-4 compatible key

**"WebSocket connection failed"**
- Backend must be running on port 8000
- Check CORS settings in `api.py`
- Verify `FRONTEND_URL` is set to `http://localhost:3000`

**"Analysis stuck at X%"**
- Large repos take time (5-10 minutes for 1000+ files)
- Check backend logs for errors
- Ensure sufficient disk space for temp cloning

### Getting Help

- 📧 Open an [issue](https://github.com/yourusername/code-intel/issues)
- 💬 Check existing [discussions](https://github.com/yourusername/code-intel/discussions)
- 🐛 Submit bug reports with logs and repo details

---

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- OpenAI for GPT-4 API
- LangChain for agent orchestration framework
- ChromaDB for vector database
- FastAPI for excellent API framework
- React team for the UI library

---

<div align="center">

**Built with ❤️ by [Oussama Abouyahia](https://github.com/yourusername)**

[⬆ Back to Top](#-code-intel)

</div>
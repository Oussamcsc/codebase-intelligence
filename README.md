# 🧠 Codebase Intelligence

> **Graph-powered code analysis that goes beyond traditional linting**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-latest-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://reactjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An intelligent code review system that combines **static graph analysis** (DFS, BFS, call graphs) with **GPT-4** to provide comprehensive, evidence-based code reviews. Goes beyond syntax checking to analyze circular dependencies, dead code, function impact, and architectural patterns.

---

## ✨ Key Features

### 🔍 **Graph-Based Static Analysis**
- **Circular dependency detection** using depth-first search
- **Dead code identification** through call graph analysis
- **Impact analysis** with breadth-first traversal
- **Function complexity** calculation (cyclomatic complexity)
- **Type hint coverage** tracking

### 🤖 **AI-Powered Insights**
- **GPT-4 integration** for synthesized recommendations
- **RAG-enhanced reviews** using ChromaDB vector database
- **Context-aware suggestions** based on codebase patterns
- **Prioritized issue reporting** (Critical → Warning → Suggestion)

### 📊 **Comprehensive Metrics**
- Function-level impact scores
- Dependency graph visualization data
- Code quality scoring (1-10 scale)
- Issue categorization and severity levels
- Detailed evidence for each finding

### 🚀 **Production Ready**
- Full-stack web interface (React + FastAPI)
- REST API for CI/CD integration
- Batch repository analysis
- Export reports (JSON format)

---

## 🏗️ Architecture
```
┌──────────────────────────────────────────────────────────┐
│                    Repository Input                       │
└────────────────────────┬─────────────────────────────────┘
                         │
                         v
┌──────────────────────────────────────────────────────────┐
│              Codebase Analyzer (Graph Builder)           │
│  • Parse AST for all Python files                        │
│  • Build dependency graph (file-level)                   │
│  • Build call graph (function-level)                     │
│  • Calculate complexity metrics                          │
└────────────────────────┬─────────────────────────────────┘
                         │
                         v
┌──────────────────────────────────────────────────────────┐
│              Static Analysis Engine                       │
│  • DFS for circular dependencies                         │
│  • Call graph for dead code detection                    │
│  • BFS for impact analysis                               │
│  • Type hint validation                                  │
└────────────────────────┬─────────────────────────────────┘
                         │
                         v
┌──────────────────────────────────────────────────────────┐
│                   GPT Review Layer                        │
│  • RAG with ChromaDB (best practices)                    │
│  • GPT-4 synthesis & prioritization                      │
│  • Root cause analysis                                   │
└────────────────────────┬─────────────────────────────────┘
                         │
                         v
┌──────────────────────────────────────────────────────────┐
│                   Structured Output                       │
│  • JSON report with evidence                             │
│  • Severity-based grouping                               │
│  • Actionable recommendations                            │
└──────────────────────────────────────────────────────────┘
```

**Tech Stack:**
- **Backend:** Python 3.11, FastAPI, AST parsing
- **Frontend:** React 18, Axios
- **AI/ML:** OpenAI GPT-4, ChromaDB (RAG), Sentence Transformers
- **Analysis:** NetworkX-style graph algorithms (DFS/BFS)

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** and npm
- **OpenAI API key** ([Get one here](https://platform.openai.com/api-keys))

### Installation
```bash
# 1. Clone repository
git clone git@github.com:Oussamcsc/codebase-intelligence.git
cd codebase-intelligence

# 2. Backend setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements-full.txt

# 3. Configure API key
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY=sk-your-key-here

# 4. Start backend
python api.py
# API runs at http://localhost:8000

# 5. Frontend setup (new terminal)
cd web
npm install
npm start
# UI opens at http://localhost:3000
```

---

## 💻 Usage

### Web Interface

1. **Open** `http://localhost:3000`
2. **Paste** GitHub repository URL (e.g., `https://github.com/psf/requests`)
3. **Click** "Analyze Repository"
4. **Wait** 5-15 minutes (depends on repo size)
5. **Review** results with expandable issues grouped by severity

### API Endpoints

**Health Check**
```bash
curl http://localhost:8000/health
```

**Analyze Repository**
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "repository_url": "https://github.com/psf/requests",
    "branch": "main"
  }'
```

**Response:**
```json
{
  "repository": "https://github.com/psf/requests",
  "branch": "main",
  "files_analyzed": 29,
  "total_issues": 210,
  "results": [
    {
      "file_path": "src/requests/sessions.py",
      "review": {
        "overall_quality": "6",
        "summary": "High complexity functions detected...",
        "critical_findings": {
          "correctness_issues": 0,
          "stability_risks": 2,
          "performance_problems": 1,
          "maintainability_debt": 4
        },
        "issues": [
          {
            "issue_type": "Critical",
            "location": "Line 159",
            "bug_risk": "Circular dependency detected",
            "evidence": {
              "cycle": ["sessions.py", "cookies.py", "compat.py"],
              "detection_method": "DFS_on_dependency_graph"
            }
          }
        ]
      }
    }
  ]
}
```

---

## 📊 Example Analysis

**Tested on:** Python `requests` library (29 files, ~10K LOC)

**Results:**
- ✅ **210 issues found** in ~15 minutes
- 🔴 **3 critical issues** (circular dependencies, security risks)
- ⚠️ **45 warnings** (dead code, high complexity, unused imports)
- 💡 **162 suggestions** (missing type hints, documentation)

**Key Findings:**
- Circular dependency: `cookies.py → compat.py → _internal_utils.py`
- 20 dead test functions (not being executed)
- High-impact function: `merge_setting()` called by 15+ functions
- Security: `exec()` usage in `setup.py`

---

## 🧪 Testing
```bash
# Run tests
pytest

# Run specific test
pytest test_code_reviewer.py -v

# Run with coverage
pytest --cov=. --cov-report=html
```

---

## 📈 Performance

**Benchmarks:**
- **Small repo** (<10 files): 2-5 minutes
- **Medium repo** (10-50 files): 5-15 minutes  
- **Large repo** (50-100 files): 15-30 minutes

**Bottlenecks:**
- GPT-4 API calls (30-60s per file)
- Graph analysis (minimal, <1s per file)

**Optimization tips:**
- Use `gpt-4o-mini` for 10x speedup
- Filter out test files
- Skip files >100KB

---

## 🎯 How It Works

### 1. **Graph Construction**
```python
# Parse all Python files
for file in repo.glob("*.py"):
    tree = ast.parse(file.read_text())
    # Extract functions, classes, imports
    # Build dependency_graph[file] = {imported_files}
    # Build function_call_graph[func] = {called_functions}
```

### 2. **Static Analysis**
```python
# Circular dependencies (DFS)
def find_cycles(graph):
    visited, rec_stack = set(), set()
    for node in graph:
        dfs(node, visited, rec_stack, path=[])
    return cycles

# Dead code (call graph)
def find_dead_code(functions):
    return [f for f in functions if not f.called_by]

# Impact analysis (BFS)
def calculate_impact(func):
    upstream = bfs_callers(func)
    downstream = bfs_callees(func)
    return ImpactScore(upstream, downstream, complexity)
```

### 3. **GPT Synthesis**
```python
# Combine static analysis + RAG
issues = codebase_analyzer.analyze_file(file)
context = rag_db.query(issues, top_k=10)
review = gpt4.generate(issues + context)
```

---

## 🛣️ Roadmap

**✅ Phase 1 - Core Engine** (Complete)
- [x] Graph-based static analysis
- [x] GPT-4 integration with RAG
- [x] Web interface
- [x] REST API

**🚧 Phase 2 - Polish** (In Progress)
- [ ] Speed optimizations (gpt-4o-mini, caching)
- [ ] Better GPT prompts (reduce verbosity)
- [ ] Export to PDF/Markdown
- [ ] Dark mode UI

**📋 Phase 3 - Scale** (Planned)
- [ ] GitHub PR integration (automated comments)
- [ ] CI/CD plugins (GitHub Actions, GitLab CI)
- [ ] Multi-language support (JavaScript, TypeScript, Java)
- [ ] Team dashboards & analytics

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repo
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

**Development setup:**
```bash
# Install dev dependencies
pip install -r requirements-full.txt
black .
flake8 .

# Run tests
pytest -v
```

---

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **OpenAI** for GPT-4 API
- **ChromaDB** for vector database
- **FastAPI** for backend framework
- **Python `ast` module** for code parsing

---

## 📧 Contact

**Oussama Abouyahia**  
📧 [oabouyahia@gmail.com](mailto:oabouyahia@gmail.com)  
🔗 [github.com/Oussamcsc/codebase-intelligence](https://github.com/Oussamcsc/codebase-intelligence)

---

<div align="center">

**⭐ Star this repo if you find it useful!**

Built with ❤️ using Python, React, and GPT-4

</div>
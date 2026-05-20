# api.py - Updated to use server-side state store, removing dependency on github_auth.py's state validation

import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import ast
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse # Add RedirectResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Callable
import uvicorn
from Code_reviewer import CodeReviewer
import json
import tempfile
import asyncio
import uuid
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlencode
import gc
import time
from datetime import datetime
import sqlite3
from contextlib import contextmanager
import secrets # Import secrets for token generation
import httpx # Import httpx for async requests in exchange_code_for_token if needed, otherwise remove
from config import (
    ANALYSIS_MODE,
    API_HOST,
    API_PORT,
    CHROMA_HOST,
    CHROMA_PORT,
    DB_PATH,
    EMBEDDING_MODEL,
    ENABLE_RAG,
    FRONTEND_REDIRECT_BASE,
    FRONTEND_URL,
    GITHUB_CLIENT_ID,
    GITHUB_CLIENT_SECRET,
    GPT_REVIEW_MODEL,
    GPT_TIMEOUT_SECONDS,
    MAX_ANALYSIS_FILES,
    OPENAI_API_KEY,
    OAUTH_COOKIE_SECURE,
    REDIRECT_URI,
    VECTOR_DB_PATH,
)


# --- NEW: SERVER-SIDE STATE STORE FOR OAUTH ---
oauth_states_store = {} # Dictionary to store state values server-side, keyed by a unique ID


app = FastAPI(
    title="Enhanced Modular AI Code Review API",
    description="Comprehensive code review with codebase analysis, pattern matching, type checking, and duplicate detection",
    version="2.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize comprehensive code reviewer lazily enough for health/config endpoints to work
# even when a fresh clone has not configured OPENAI_API_KEY yet.
reviewer = None
if OPENAI_API_KEY:
    reviewer = CodeReviewer(
        openai_api_key=OPENAI_API_KEY,
        embedding_model=EMBEDDING_MODEL,
        vector_db_path=VECTOR_DB_PATH,
        chroma_host=CHROMA_HOST,
        chroma_port=CHROMA_PORT,
        analysis_mode=ANALYSIS_MODE,
        enable_rag=ENABLE_RAG,
        gpt_review_model=GPT_REVIEW_MODEL,
        gpt_timeout_seconds=GPT_TIMEOUT_SECONDS,
    )
else:
    print("⚠️ OPENAI_API_KEY not configured. Health/config endpoints are available; analysis endpoints will return 503.")


def require_reviewer() -> CodeReviewer:
    if reviewer is None:
        raise HTTPException(
            status_code=503,
            detail="OPENAI_API_KEY is not configured. Set it in .env to enable code analysis."
        )
    return reviewer

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_database():
    """Initialize SQLite database for result persistence"""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS analysis_jobs (
                job_id TEXT PRIMARY KEY,
                repo_url TEXT NOT NULL,
                branch TEXT NOT NULL,
                status TEXT NOT NULL,
                progress INTEGER DEFAULT 0,
                current_task TEXT,
                files_analyzed INTEGER DEFAULT 0,
                total_files INTEGER DEFAULT 0,
                results_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                error TEXT
            )
        """)
        conn.commit()
    print("✅ Database initialized")

# Initialize on startup
@app.on_event("startup")
async def startup_event():
    """Initialize knowledge base and codebase analysis on startup"""
    try:
        print("🚀 Initializing Enhanced Code Review System...")
        # Initialize database
        init_database()
        if reviewer is None:
            print("⚠️ Skipping analyzer startup: OPENAI_API_KEY is not configured")
            return
        if ENABLE_RAG:
            reviewer.initialize_knowledge_base()
            print("✅ Knowledge base initialized")
        else:
            print("⏭️ Knowledge base disabled (ENABLE_RAG=false)")
        reviewer.enable_codebase_analysis(".")
        print("✅ Codebase analysis enabled")
    except Exception as e:
        print(f"⚠️ Warning: Could not fully initialize system: {e}")

# Request/Response models
class CodeReviewRequest(BaseModel):
    code: str = Field(..., description="Code to review")
    language: str = Field(default="python", description="Programming language")
    file_path: Optional[str] = Field(None, description="File path for codebase-aware analysis")
    context: Optional[str] = Field(None, description="Additional context")

class FileReviewRequest(BaseModel):
    file_path: str = Field(..., description="Path to file to review")
    context: Optional[str] = Field(None, description="Additional context")

class BestPracticeRequest(BaseModel):
    practice: str = Field(..., description="Best practice description")
    category: str = Field(..., description="Category (e.g., security, performance)")
    metadata: Optional[dict] = Field(None, description="Additional metadata")

class CommonIssueRequest(BaseModel):
    issue: str = Field(..., description="Common issue description")
    category: str = Field(..., description="Category (e.g., bugs, security)")
    metadata: Optional[dict] = Field(None, description="Additional metadata")

class AnalysisResponse(BaseModel):
    total_verified_issues: int
    analyzer_counts: Dict[str, int]
    issues: List[Dict[str, Any]]
    overall_quality: str
    summary: str
    strengths: List[str]
    recommendations: List[str]

class GitHubRepoRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL (e.g., https://github.com/user/repo)")
    branch: str = Field(default="main", description="Branch to analyze")
    files_pattern: str = Field(default="*.py", description="File pattern to analyze")
    max_files: int = Field(default=MAX_ANALYSIS_FILES, ge=1, le=500, description="Maximum files to analyze for latency control")
    analysis_mode: str = Field(default=ANALYSIS_MODE, description="fast or detailed")

class AnalysisJobResponse(BaseModel):
    job_id: str
    status: str
    message: str
    share_url: str  # NEW: Shareable link

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int
    current_task: str
    files_analyzed: int
    total_files: int
    results_available: bool

# Endpoints
@app.get("/")
async def root():
    """Root endpoint with API info"""
    return {
        "name": "Enhanced Modular AI Code Review API",
        "version": "2.1.0",
        "description": "Comprehensive code analysis with 4 specialized analyzers",
        "analyzers": [
            "Codebase Analyzer (dependencies, dead code, impact)",
            "Pattern Matcher (AST antipatterns, complexity)",
            "Type Analyzer (signatures, type hints)",
            "Duplicate Detector (code duplication)"
        ],
        "new_features": [
            "Database persistence",
            "Export to PDF/JSON",
            "Shareable analysis links",
            "Real-time progress tracking"
        ],
        "endpoints": {
            "POST /review": "Comprehensive code review",
            "POST /review-file": "Review file by path",
            "POST /upload-review": "Upload and review file",
            "POST /best-practices": "Add best practice",
            "POST /common-issues": "Add common issue",
            "GET /stats": "Get system statistics",
            "GET /health": "Health check",
            "GET /analysis-results": "Get last analysis breakdown",
            "POST /github/analyze": "Start GitHub repository analysis",
            "GET /github/status/{job_id}": "Get analysis job status",
            "GET /github/results/{job_id}": "Get analysis results",
            "GET /github/share/{job_id}": "Get shareable analysis (public)",
            "GET /github/export/{job_id}/json": "Export results as JSON",
            "GET /github/export/{job_id}/pdf": "Export results as PDF",
            "WS /ws/progress/{job_id}": "Real-time progress updates",
            "DELETE /github/jobs/{job_id}": "Clean up analysis job"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy" if reviewer is not None else "degraded",
        "system": "Enhanced Modular Code Review",
        "version": "2.1.0",
        "config": {
            "openai_configured": bool(OPENAI_API_KEY),
            "github_oauth_configured": bool(GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET),
            "analysis_mode": ANALYSIS_MODE,
            "review_model": GPT_REVIEW_MODEL,
            "max_analysis_files": MAX_ANALYSIS_FILES,
            "rag_enabled": ENABLE_RAG,
        },
        "analyzers": {
            "codebase_analyzer": "✅ Active" if reviewer else "⚠️ Disabled until OPENAI_API_KEY is set",
            "pattern_matcher": "✅ Active" if reviewer else "⚠️ Disabled until OPENAI_API_KEY is set",
            "type_analyzer": "✅ Active" if reviewer else "⚠️ Disabled until OPENAI_API_KEY is set",
            "duplicate_detector": "✅ Active" if reviewer and ANALYSIS_MODE == "detailed" else "⏭️ Skipped in fast mode"
        },
        "knowledge_base": {
            "best_practices": reviewer.best_practices.count() if reviewer else 0,
            "common_issues": reviewer.common_issues.count() if reviewer else 0
        },
        "database": "✅ Connected"
    }

@app.get("/stats")
async def get_stats():
    """Get comprehensive system statistics"""
    r = require_reviewer()
    with get_db() as conn:
        cursor = conn.execute("SELECT COUNT(*) as total FROM analysis_jobs")
        total_jobs = cursor.fetchone()['total']
        cursor = conn.execute("SELECT COUNT(*) as completed FROM analysis_jobs WHERE status = 'completed'")
        completed_jobs = cursor.fetchone()['completed']
    return {
        "knowledge_base": {
            "best_practices": r.best_practices.count(),
            "common_issues": r.common_issues.count()
        },
        "last_analysis": r.last_analysis_results,
        "codebase_analysis": {
            "enabled": r.codebase_analyzer.is_analyzed,
            "files_analyzed": len(r.codebase_analyzer.all_files),
            "functions_found": len(r.codebase_analyzer.all_functions)
        },
        "jobs": {
            "total": total_jobs,
            "completed": completed_jobs
        }
    }

@app.post("/review")
async def review_code(request: CodeReviewRequest):
    """Comprehensive code review with all analyzers"""
    try:
        r = require_reviewer()
        review = r.review_code(
            code=request.code,
            language=request.language,
            file_path=request.file_path,
            context=request.context
        )
        if "error" in review:
            raise HTTPException(status_code=400, detail=review["error"])
        return review
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/review-file")
async def review_file(request: FileReviewRequest):
    """Review a file by path with full codebase analysis"""
    try:
        file_path = Path(request.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        r = require_reviewer()
        review = r.review_code(
            code=code,
            language="python",
            file_path=request.file_path,
            context=request.context
        )
        return review
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload-review")
async def upload_and_review(file: UploadFile = File(...), context: Optional[str] = None):
    """Upload a file and perform comprehensive review"""
    try:
        content = await file.read()
        code = content.decode('utf-8')
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name
        try:
            r = require_reviewer()
            review = r.review_code(
                code=code,
                language="python",
                file_path=tmp_path,
                context=context
            )
            return review
        finally:
            os.unlink(tmp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/best-practices")
async def add_best_practice(request: BestPracticeRequest):
    """Add a best practice to the knowledge base"""
    try:
        r = require_reviewer()
        r.add_best_practice(
            request.practice,
            request.category,
            request.metadata
        )
        return {
            "status": "success",
            "message": "Best practice added",
            "total_count": r.best_practices.count()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/common-issues")
async def add_common_issue(request: CommonIssueRequest):
    """Add a common issue to the knowledge base"""
    try:
        r = require_reviewer()
        r.add_common_issue(
            request.issue,
            request.category,
            request.metadata
        )
        return {
            "status": "success",
            "message": "Common issue added",
            "total_count": r.common_issues.count()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Import exchange_code_for_token from github_auth (the modified version without state validation)
from github_auth import exchange_code_for_token, get_user_repos, get_repo_pull_requests


@app.get("/auth/github")
def start_github_oauth(response: Response):
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        raise HTTPException(
            status_code=500,
            detail="GitHub OAuth is not configured. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in .env."
        )

    # Generate random state and state_id
    state = secrets.token_urlsafe(16)
    state_id = str(uuid.uuid4())

    oauth_states_store[state_id] = {
        "state": state,
        "timestamp": time.time()
    }

    response.set_cookie(
        key="github_oauth_state_id",
        value=state_id,
        httponly=True,
        samesite="none" if OAUTH_COOKIE_SECURE else "lax",
        secure=OAUTH_COOKIE_SECURE,
        max_age=600
    )

    oauth_params = urlencode({
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "state": state_id,
        "scope": "repo read:user",
    })
    oauth_url = f"https://github.com/login/oauth/authorize?{oauth_params}"
    return {"oauth_url": oauth_url}


@app.get("/auth/github/callback")
async def github_oauth_callback(code: str, state: str, request: Request, response: Response):
    state_id_received_from_github = state
    stored_data = oauth_states_store.get(state_id_received_from_github)

    if not stored_data:
        response.delete_cookie("github_oauth_state_id")
        raise HTTPException(status_code=400, detail="Invalid or expired state token")

    if state_id_received_from_github in oauth_states_store:
        del oauth_states_store[state_id_received_from_github]
    response.delete_cookie("github_oauth_state_id")

    # Pass REDIRECT_URI from env
    result = exchange_code_for_token(code, REDIRECT_URI)
    access_token = result["access_token"]
    username = result["username"]
    avatar_url = result["avatar_url"]

    # Use URL fragment so the access token is handled client-side and is not
    # written to frontend server access logs.
    redirect_path = "/github"
    redirect_params = urlencode({
        "access_token": access_token,
        "username": username,
        "avatar_url": avatar_url or "",
    })
    redirect_url = f"{FRONTEND_REDIRECT_BASE}{redirect_path}#{redirect_params}"
    return RedirectResponse(url=redirect_url)

@app.get("/github/repos")
async def get_repos(access_token: str, page: int = 1):
    """Get user's GitHub repositories"""
    try:
        repos = get_user_repos(access_token, page=page)
        return {
            "status": "success",
            "repos": repos
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/github/repos/{owner}/{repo}/pulls")
async def get_pull_requests(owner: str, repo: str, access_token: str):
    """Get pull requests for a repository"""
    try:
        prs = get_repo_pull_requests(access_token, f"{owner}/{repo}")
        return {
            "status": "success",
            "pull_requests": prs
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/analysis-results")
async def get_last_analysis():
    """Get detailed breakdown of last analysis"""
    r = require_reviewer()
    return {
        "status": "success",
        "last_analysis": r.last_analysis_results,
        "analysis_details": {
            "codebase_issues": len(r.last_analysis_results.get('codebase_issues', [])),
            "pattern_issues": len(r.last_analysis_results.get('pattern_issues', [])),
            "type_issues": len(r.last_analysis_results.get('type_issues', [])),
            "duplicate_issues": len(r.last_analysis_results.get('duplicate_issues', [])),
            "total_verified": r.last_analysis_results.get('total_issues', 0)
        }
    }


@app.get("/codebase-info")
async def get_codebase_info():
    """Get information about the analyzed codebase"""
    r = require_reviewer()
    if not r.codebase_analyzer.is_analyzed:
        raise HTTPException(status_code=404, detail="Codebase not analyzed. Run analysis first.")

    return {
        "analyzed": True,
        "files": len(r.codebase_analyzer.all_files),
        "functions": len(r.codebase_analyzer.all_functions),
        "dependencies": len(r.codebase_analyzer.dependency_graph),
        "sample_files": list(r.codebase_analyzer.all_files.keys())[:10]
    }


@app.post("/analyze-function/{function_name}")
async def analyze_function_impact(function_name: str, file_path: str = None):
    """Get detailed impact analysis for a specific function"""
    try:
        r = require_reviewer()
        if not file_path:
            matching_functions = []
            for func_key in r.codebase_analyzer.all_functions.keys():
                if function_name in func_key:
                    matching_functions.append(func_key)

            if not matching_functions:
                raise HTTPException(status_code=404, detail=f"Function '{function_name}' not found")
            elif len(matching_functions) > 1:
                return {
                    "error": "Multiple functions found",
                    "matches": matching_functions,
                    "message": "Please specify file_path parameter"
                }
            else:
                func_key = matching_functions[0]
        else:
            func_key = f"{file_path}::{function_name}"

        impact_analysis = r.codebase_analyzer.get_function_impact_chain(func_key)
        dependency_analysis = r.codebase_analyzer.analyze_function_dependencies(func_key)

        return {
            "function": function_name,
            "file": file_path,
            "impact_analysis": impact_analysis,
            "dependency_analysis": dependency_analysis
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, job_id: str, websocket: WebSocket):
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = []
        self.active_connections[job_id].append(websocket)
        print(f"✅ WebSocket connected for job {job_id}")

    def disconnect(self, job_id: str, websocket: WebSocket):
        if job_id in self.active_connections:
            self.active_connections[job_id].remove(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
        print(f"🔌 WebSocket disconnected for job {job_id}")

    async def broadcast_to_job(self, job_id: str, message: dict):
        """Send message to all connections watching this job"""
        if job_id in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[job_id]:
                try:
                    await connection.send_json(message)
                except:
                    dead_connections.append(connection)

            # Clean up dead connections
            for dead in dead_connections:
                self.disconnect(job_id, dead)


manager = ConnectionManager()


# Helper functions
def clone_github_repo(repo_url: str, branch: str = "main") -> str:
    """Clone GitHub repo to temporary directory"""
    temp_dir = tempfile.mkdtemp(prefix="code-review-")
    try:
        subprocess.run([
            "git", "clone", "--depth", "1", "--branch", branch,
            repo_url, temp_dir
        ], check=True, capture_output=True, text=True)
        return temp_dir
    except subprocess.CalledProcessError as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=f"Failed to clone repository: {e.stderr}")


def update_job_status(job_id: str, **kwargs):
    """Update job status in database AND broadcast via WebSocket"""
    with get_db() as conn:
        # Build UPDATE query dynamically
        updates = []
        values = []
        for key, value in kwargs.items():
            if key in ['status', 'progress', 'current_task', 'files_analyzed', 'total_files', 'results_json', 'error']:
                updates.append(f"{key} = ?")
                if key == 'results_json' and isinstance(value, (dict, list)):
                    values.append(json.dumps(value))
                else:
                    values.append(value)

        if kwargs.get('status') == 'completed':
            updates.append("completed_at = ?")
            values.append(datetime.now().isoformat())

        values.append(job_id)
        query = f"UPDATE analysis_jobs SET {', '.join(updates)} WHERE job_id = ?"
        conn.execute(query, values)
        conn.commit()

    # Broadcast update via WebSocket
    asyncio.create_task(manager.broadcast_to_job(job_id, {
        "job_id": job_id,
        **kwargs
    }))

    print(f"✅ Job {job_id} updated: {kwargs}")



def _repo_relative_path(file_path: Path, repo_dir: str) -> str:
    try:
        resolved_file = Path(os.path.realpath(file_path))
        resolved_repo = Path(os.path.realpath(repo_dir))
        return str(resolved_file.relative_to(resolved_repo))
    except ValueError:
        return str(file_path.relative_to(repo_dir)) if str(file_path).startswith(str(repo_dir)) else file_path.name


def _collect_fast_repository_evidence(
    analysis_reviewer: CodeReviewer,
    repo_dir: str,
    matching_files: List[Path],
    repo_url: str,
    branch: str,
    discovered_files: int,
    max_files: int,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    stage_callback: Optional[Callable[[int, str], None]] = None,
) -> Dict[str, Any]:
    """Run deterministic/static analyzers across the repo, then one repo-level LLM pass."""
    telemetry = {
        "timings_ms": {},
        "strategy": "single repository-level LLM call after static evidence collection",
    }
    evidence_scan_start = time.perf_counter()
    all_issues = []
    file_summaries = []
    successful_files = 0
    failed_files = 0

    for i, file_path in enumerate(matching_files):
        try:
            absolute_file_path = file_path.resolve()
            rel_path = _repo_relative_path(file_path, repo_dir)
            if progress_callback:
                progress_callback(i + 1, len(matching_files), rel_path)
            with open(absolute_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                code = f.read()

            structure = analysis_reviewer._analyze_code_structure(code)
            file_summaries.append({
                "file_path": rel_path,
                "lines": structure.get("lines", len(code.splitlines())),
                "functions": [item.get("name") for item in structure.get("functions", [])[:20]],
                "classes": [item.get("name") for item in structure.get("classes", [])[:20]],
                "imports_count": len(structure.get("imports", [])),
            })

            try:
                codebase_issues = analysis_reviewer.codebase_analyzer.analyze_file(str(absolute_file_path))
                all_issues.extend(analysis_reviewer._convert_codebase_issues(codebase_issues, code, rel_path))
            except Exception as e:
                print(f"⚠️ Codebase evidence failed for {rel_path}: {e}")

            try:
                tree = ast.parse(code)
                pattern_issues = analysis_reviewer.pattern_matcher.find_antipatterns(tree, rel_path, code)
                all_issues.extend(analysis_reviewer._convert_pattern_issues(pattern_issues, code, rel_path))
            except Exception as e:
                print(f"⚠️ Pattern evidence failed for {rel_path}: {e}")

            successful_files += 1
        except Exception as e:
            failed_files += 1
            print(f"❌ Evidence collection failed for {file_path.name}: {e}")

    telemetry["timings_ms"]["evidence_scan"] = round((time.perf_counter() - evidence_scan_start) * 1000)

    if stage_callback:
        stage_callback(76, "Running repository type analysis...")
    type_analysis_start = time.perf_counter()
    try:
        previous_cwd = os.getcwd()
        os.chdir(repo_dir)
        try:
            type_issues = analysis_reviewer.type_analyzer.analyze_types(
                analysis_reviewer.codebase_analyzer.all_functions,
                analysis_reviewer.codebase_analyzer.all_files,
                target_file=None,
            )
        finally:
            os.chdir(previous_cwd)
        for issue in type_issues[:100]:
            issue_file = getattr(issue, "file_path", None) or "repository"
            all_issues.extend(analysis_reviewer._convert_type_issues([issue], "", issue_file))
    except Exception as e:
        print(f"⚠️ Repository type evidence failed: {e}")
    telemetry["timings_ms"]["type_analysis"] = round((time.perf_counter() - type_analysis_start) * 1000)

    if stage_callback:
        stage_callback(80, "Prioritizing high-signal findings...")
    filtering_start = time.perf_counter()
    high_impact_issues = analysis_reviewer._filter_senior_engineer_issues(all_issues)
    telemetry["timings_ms"]["issue_filtering"] = round((time.perf_counter() - filtering_start) * 1000)
    metadata = {
        "files_discovered": discovered_files,
        "files_analyzed": successful_files,
        "files_failed": failed_files,
        "files_capped_at": max_files,
        "functions_found": len(analysis_reviewer.codebase_analyzer.all_functions),
        "parsed_files": len(analysis_reviewer.codebase_analyzer.all_files),
        "raw_static_issues": len(all_issues),
        "high_impact_issues": len(high_impact_issues),
        "latency_strategy": "single repository-level LLM call after static evidence collection",
        "telemetry": telemetry,
    }

    if stage_callback:
        stage_callback(85, "Synthesizing repository-level review with LLM...")
    llm_review_start = time.perf_counter()
    review = analysis_reviewer.review_repository_evidence(
        repo_url=repo_url,
        branch=branch,
        file_summaries=file_summaries,
        issues=high_impact_issues,
        metadata=metadata,
    )
    telemetry["timings_ms"]["llm_review"] = round((time.perf_counter() - llm_review_start) * 1000)
    telemetry["timings_ms"]["fast_repository_total"] = sum(telemetry["timings_ms"].values())
    review.setdefault("metadata", metadata)
    review["metadata"]["telemetry"] = telemetry

    return {
        "repository": repo_url,
        "branch": branch,
        "files_analyzed": successful_files,
        "total_files_discovered": discovered_files,
        "total_files_attempted": len(matching_files),
        "analysis_mode": "fast",
        "max_files": max_files,
        "files_failed": failed_files,
        "total_issues": len(review.get("issues", [])),
        "repository_review": review,
        "telemetry": telemetry,
        "results": [{"file_path": "repository", "review": review}],
    }


async def analyze_github_repo_background(job_id: str, repo_url: str, branch: str, files_pattern: str, max_files: int, analysis_mode: str):
    """Background task to analyze GitHub repository with REAL progress tracking"""
    print(f"\n{'=' * 80}")
    print(f"🚀 STARTING ANALYSIS JOB: {job_id}")
    print(f"{'=' * 80}\n")

    repo_dir = None
    analysis_reviewer = None
    job_start = time.perf_counter()
    telemetry = {"timings_ms": {}}

    try:
        # Stage 1: Cloning (0-15%)
        update_job_status(job_id, status="running", progress=5, current_task="Cloning repository...")

        clone_start = time.perf_counter()
        repo_dir = clone_github_repo(repo_url, branch)
        telemetry["timings_ms"]["clone"] = round((time.perf_counter() - clone_start) * 1000)
        print(f"✅ Repo cloned to: {repo_dir}")

        # Stage 2: Scanning (15-25%)
        update_job_status(job_id, progress=15, current_task="Scanning files...")

        scan_start = time.perf_counter()
        ignored_parts = {".git", "__pycache__", ".venv", "venv", "env", "node_modules", "dist", "build", ".next"}
        matching_files = []
        for pattern in files_pattern.split(","):
            pattern = pattern.strip()
            for file_path in Path(repo_dir).rglob(pattern):
                if not file_path.is_file():
                    continue
                if any(part in ignored_parts for part in file_path.parts):
                    continue
                if file_path.stat().st_size >= 1024 * 1024:
                    continue
                matching_files.append(file_path)

        matching_files = sorted(set(matching_files), key=lambda path: (len(path.parts), str(path)))
        discovered_files = len(matching_files)
        if len(matching_files) > max_files:
            matching_files = matching_files[:max_files]
        telemetry["timings_ms"]["file_discovery"] = round((time.perf_counter() - scan_start) * 1000)

        print(f"📁 Found {discovered_files} files; analyzing {len(matching_files)}")
        update_job_status(
            job_id,
            progress=25,
            current_task=f"Found {discovered_files} files; analyzing {len(matching_files)}",
            total_files=len(matching_files)
        )

        # Stage 3: Building graph (25-35%)
        is_large_repo = len(matching_files) > 100 or analysis_mode.lower() == "fast"
        update_job_status(job_id, progress=30, current_task="Building codebase graph...")

        analysis_reviewer = CodeReviewer(
            openai_api_key=OPENAI_API_KEY,
            embedding_model=EMBEDDING_MODEL,
            vector_db_path=VECTOR_DB_PATH,
            chroma_host=CHROMA_HOST,
            chroma_port=CHROMA_PORT,
            skip_duplicate_detection=is_large_repo,
            analysis_mode=analysis_mode,
            enable_rag=ENABLE_RAG and analysis_mode.lower() == "detailed",
            gpt_review_model=GPT_REVIEW_MODEL,
            gpt_timeout_seconds=GPT_TIMEOUT_SECONDS,
        )

        graph_start = time.perf_counter()
        try:
            # CRITICAL FIX: Pass repo_dir to enable_codebase_analysis
            print(f"🔧 Building codebase graph for: {repo_dir}")
            analysis_reviewer.enable_codebase_analysis(repo_dir)
            print("✅ Codebase graph built")
        except Exception as e:
            print(f"⚠️ Graph build warning: {e}")
        telemetry["timings_ms"]["codebase_graph"] = round((time.perf_counter() - graph_start) * 1000)

        update_job_status(job_id, progress=35, current_task="Starting repository-level evidence scan...")

        if analysis_mode.lower() == "fast":
            def fast_progress(current: int, total: int, rel_path: str) -> None:
                progress = 35 + int(current / max(total, 1) * 40)
                update_job_status(
                    job_id,
                    progress=progress,
                    files_analyzed=current,
                    current_task=f"Collecting evidence from {rel_path} ({current}/{total})"
                )

            def fast_stage(progress: int, task: str) -> None:
                update_job_status(job_id, progress=progress, current_task=task)

            results = _collect_fast_repository_evidence(
                analysis_reviewer=analysis_reviewer,
                repo_dir=repo_dir,
                matching_files=matching_files,
                repo_url=repo_url,
                branch=branch,
                discovered_files=discovered_files,
                max_files=max_files,
                progress_callback=fast_progress,
                stage_callback=fast_stage,
            )
            results.setdefault("telemetry", {}).setdefault("timings_ms", {})
            results["telemetry"]["timings_ms"] = {**telemetry["timings_ms"], **results["telemetry"]["timings_ms"]}
            results["telemetry"]["timings_ms"]["job_total"] = round((time.perf_counter() - job_start) * 1000)
            if "repository_review" in results:
                results["repository_review"].setdefault("metadata", {})["telemetry"] = results["telemetry"]
            update_job_status(
                job_id,
                status="completed",
                progress=100,
                files_analyzed=results["files_analyzed"],
                current_task=f"Complete! Repository-level review analyzed {results['files_analyzed']}/{len(matching_files)} files",
                results_json=results
            )
            print(f"\n🏁 COMPLETE: repository-level fast review, {results['files_analyzed']}/{len(matching_files)} files")
            if repo_dir and os.path.exists(repo_dir):
                shutil.rmtree(repo_dir, ignore_errors=True)
                print(f"🧹 Cleaned up: {repo_dir}")
            if analysis_reviewer:
                del analysis_reviewer
            gc.collect()
            return

        update_job_status(job_id, progress=35, current_task="Starting file analysis...")

        # Stage 4: Analyze files (35-95%)
        all_results = []
        successful_files = 0
        failed_files = 0

        for i, file_path in enumerate(matching_files):
            try:
                # Use absolute path for reading
                absolute_file_path = file_path.resolve()

                with open(absolute_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    code = f.read()

                # Calculate relative path for display
                try:
                    resolved_file = Path(os.path.realpath(file_path))
                    resolved_repo = Path(os.path.realpath(repo_dir))
                    rel_path = str(resolved_file.relative_to(resolved_repo))
                except ValueError:
                    rel_path = str(file_path.relative_to(repo_dir)) if str(file_path).startswith(
                        str(repo_dir)) else file_path.name

                # Calculate progress (35% to 95% range)
                progress = 35 + int((i + 1) / len(matching_files) * 60)

                # UPDATE BEFORE analyzing (so frontend sees it)
                update_job_status(
                    job_id,
                    progress=progress,
                    files_analyzed=i + 1,
                    current_task=f"Analyzing {rel_path} ({i + 1}/{len(matching_files)})"
                )

                print(f"\n📄 [{i + 1}/{len(matching_files)}] Analyzing: {rel_path}")

                # CRITICAL FIX: Pass ABSOLUTE file path to review_code
                # This ensures codebase analyzer can find the file
                review = analysis_reviewer.review_code(
                    code=code,
                    language="python",
                    file_path=str(absolute_file_path),  # ← ABSOLUTE PATH
                    context=f"GitHub repo: {repo_url}"
                )

                if "error" not in review:
                    all_results.append({
                        "file_path": rel_path,  # Display relative path
                        "review": review
                    })
                    successful_files += 1
                    print(f"✅ {len(review.get('issues', []))} issues found")
                else:
                    failed_files += 1
                    print(f"❌ Error: {review.get('error')}")

            except Exception as e:
                failed_files += 1
                print(f"❌ Exception analyzing {file_path.name}: {e}")
                continue

        # Stage 5: Finalizing (95-100%)
        update_job_status(job_id, progress=95, current_task="Finalizing results...")

        total_issues = sum(len(r["review"].get("issues", [])) for r in all_results)

        telemetry["timings_ms"]["job_total"] = round((time.perf_counter() - job_start) * 1000)

        results = {
            "repository": repo_url,
            "branch": branch,
            "files_analyzed": successful_files,
            "total_files_discovered": discovered_files,
            "total_files_attempted": len(matching_files),
            "analysis_mode": analysis_mode,
            "max_files": max_files,
            "files_failed": failed_files,
            "total_issues": total_issues,
            "telemetry": telemetry,
            "results": all_results
        }

        print(f"\n🏁 COMPLETE: {successful_files}/{len(matching_files)} files, {total_issues} issues")

        # Save to database
        update_job_status(
            job_id,
            status="completed",
            progress=100,
            current_task=f"Complete! Analyzed {successful_files}/{len(matching_files)} files",
            results_json=results
        )

        # Cleanup
        if repo_dir and os.path.exists(repo_dir):
            shutil.rmtree(repo_dir, ignore_errors=True)
            print(f"🧹 Cleaned up: {repo_dir}")

        if analysis_reviewer:
            del analysis_reviewer
        gc.collect()

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

        update_job_status(
            job_id,
            status="failed",
            current_task=f"Error: {str(e)[:100]}",
            error=str(e)
        )

        # Cleanup on error
        try:
            if repo_dir and os.path.exists(repo_dir):
                shutil.rmtree(repo_dir, ignore_errors=True)
            if analysis_reviewer:
                del analysis_reviewer
            gc.collect()
        except Exception as cleanup_error:
            print(f"⚠️ Cleanup error: {cleanup_error}")

@app.post("/github/analyze", response_model=AnalysisJobResponse)
async def analyze_github_repo(request: GitHubRepoRequest, background_tasks: BackgroundTasks):
    """Start analysis of a GitHub repository"""
    try:
        job_id = str(uuid.uuid4())

        # Save to database
        with get_db() as conn:
            conn.execute("""
                INSERT INTO analysis_jobs 
                (job_id, repo_url, branch, status, progress, current_task, files_analyzed, total_files)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (job_id, request.repo_url, request.branch, "pending", 0, "Initializing...", 0, 0))
            conn.commit()

        # Start background analysis
        background_tasks.add_task(
            analyze_github_repo_background,
            job_id,
            request.repo_url,
            request.branch,
            request.files_pattern,
            request.max_files,
            request.analysis_mode
        )

        # Generate shareable URL using environment variable or default
        share_url = f"{FRONTEND_URL}/share/{job_id}"

        return AnalysisJobResponse(
            job_id=job_id,
            status="pending",
            message="Analysis started. Use /github/status/{job_id} to track progress.",
            share_url=share_url
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/github/status/{job_id}", response_model=JobStatusResponse)
async def get_analysis_status(job_id: str):
    """Get status of a GitHub repository analysis job"""
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT job_id, status, progress, current_task, files_analyzed, total_files
            FROM analysis_jobs WHERE job_id = ?
        """, (job_id,))
        job = cursor.fetchone()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job['job_id'],
        status=job['status'],
        progress=job['progress'],
        current_task=job['current_task'],
        files_analyzed=job['files_analyzed'],
        total_files=job['total_files'],
        results_available=job['status'] == 'completed'
    )


@app.get("/github/results/{job_id}")
async def get_analysis_results(job_id: str):
    """Get results of a completed analysis"""
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT status, results_json FROM analysis_jobs WHERE job_id = ?
        """, (job_id,))
        job = cursor.fetchone()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job['status'] != 'completed':
        raise HTTPException(status_code=400, detail="Analysis not completed")

    if not job['results_json']:
        raise HTTPException(status_code=404, detail="Results not available")

    return {
        "status": "success",
        "job_id": job_id,
        "results": json.loads(job['results_json'])
    }


@app.get("/github/share/{job_id}")
async def get_shareable_analysis(job_id: str):
    """Public endpoint to view shared analysis results"""
    with get_db() as conn:
        cursor = conn.execute("""
            SELECT job_id, repo_url, branch, status, results_json, created_at, completed_at
            FROM analysis_jobs WHERE job_id = ?
        """, (job_id,))
        job = cursor.fetchone()

    if not job or job['status'] != 'completed':
        raise HTTPException(status_code=404, detail="Analysis not found or not completed")

    return {
        "job_id": job['job_id'],
        "repository": job['repo_url'],
        "branch": job['branch'],
        "analyzed_at": job['completed_at'],
        "results": json.loads(job['results_json']) if job['results_json'] else None
    }


@app.get("/github/export/{job_id}/json")
async def export_json(job_id: str):
    """Export analysis results as JSON file"""
    with get_db() as conn:
        cursor = conn.execute("SELECT results_json FROM analysis_jobs WHERE job_id = ?", (job_id,))
        job = cursor.fetchone()

    if not job or not job['results_json']:
        raise HTTPException(status_code=404, detail="Results not found")

    # Create temp file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    temp_file.write(job['results_json'])
    temp_file.close()

    return FileResponse(
        temp_file.name,
        media_type='application/json',
        filename=f'code-analysis-{job_id}.json'
    )


@app.get("/github/export/{job_id}/pdf")
async def export_pdf(job_id: str):
    """Export analysis results as PDF (requires reportlab)"""
    # This is a placeholder - you'd need to install reportlab
    # For now, return JSON with instructions
    raise HTTPException(
        status_code=501,
        detail="PDF export not yet implemented. Use /export/{job_id}/json instead."
    )


@app.websocket("/ws/progress/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str):
    """WebSocket for real-time progress updates"""
    await manager.connect(job_id, websocket)
    try:
        # Send initial status
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT status, progress, current_task, files_analyzed, total_files
                FROM analysis_jobs WHERE job_id = ?
            """, (job_id,))
            job = cursor.fetchone()

        if job:
            await websocket.send_json({
                "job_id": job_id,
                "status": job['status'],
                "progress": job['progress'],
                "current_task": job['current_task'],
                "files_analyzed": job['files_analyzed'],
                "total_files": job['total_files']
            })

        # Keep connection alive
        while True:
            try:
                # Wait for client ping or updates from broadcast
                await asyncio.sleep(1)

                # Check if job completed
                with get_db() as conn:
                    cursor = conn.execute("SELECT status FROM analysis_jobs WHERE job_id = ?", (job_id,))
                    job = cursor.fetchone()
                    if job and job['status'] in ['completed', 'failed']:
                        break
            except:
                break

    except WebSocketDisconnect:
        manager.disconnect(job_id, websocket)
    finally:
        manager.disconnect(job_id, websocket)


@app.delete("/github/jobs/{job_id}")
async def cleanup_job(job_id: str):
    """Delete a job from database"""
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM analysis_jobs WHERE job_id = ?", (job_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Job not found")

    return {"status": "success", "message": "Job deleted"}


if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host=API_HOST,
        port=API_PORT,
        reload=True
    )
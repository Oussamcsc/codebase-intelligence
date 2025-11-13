"""
FastAPI REST API for Enhanced Modular Code Review Assistant
WITH: Progress tracking, Database persistence, Export functionality
"""

import os

os.environ["TOKENIZERS_PARALLELISM"] = "false"

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
import uvicorn
from Code_reviewer import CodeReviewer
import json
import tempfile
import asyncio
import uuid
import shutil
import subprocess
from pathlib import Path
import zipfile
import gc
import time
from datetime import datetime
import sqlite3
from contextlib import contextmanager

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

# Initialize comprehensive code reviewer
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable required")

reviewer = CodeReviewer(openai_api_key=api_key)

# Database setup
DB_PATH = "code_review_results.db"


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

        reviewer.initialize_knowledge_base()
        print("✅ Knowledge base initialized")

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
        "status": "healthy",
        "system": "Enhanced Modular Code Review",
        "version": "2.1.0",
        "analyzers": {
            "codebase_analyzer": "✅ Active",
            "pattern_matcher": "✅ Active",
            "type_analyzer": "✅ Active",
            "duplicate_detector": "✅ Active"
        },
        "knowledge_base": {
            "best_practices": reviewer.best_practices.count(),
            "common_issues": reviewer.common_issues.count()
        },
        "database": "✅ Connected"
    }


@app.get("/stats")
async def get_stats():
    """Get comprehensive system statistics"""
    with get_db() as conn:
        cursor = conn.execute("SELECT COUNT(*) as total FROM analysis_jobs")
        total_jobs = cursor.fetchone()['total']

        cursor = conn.execute("SELECT COUNT(*) as completed FROM analysis_jobs WHERE status = 'completed'")
        completed_jobs = cursor.fetchone()['completed']

    return {
        "knowledge_base": {
            "best_practices": reviewer.best_practices.count(),
            "common_issues": reviewer.common_issues.count()
        },
        "last_analysis": reviewer.last_analysis_results,
        "codebase_analysis": {
            "enabled": reviewer.codebase_analyzer.is_analyzed,
            "files_analyzed": len(reviewer.codebase_analyzer.all_files),
            "functions_found": len(reviewer.codebase_analyzer.all_functions)
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
        review = reviewer.review_code(
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

        review = reviewer.review_code(
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
            review = reviewer.review_code(
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
        reviewer.add_best_practice(
            request.practice,
            request.category,
            request.metadata
        )
        return {
            "status": "success",
            "message": "Best practice added",
            "total_count": reviewer.best_practices.count()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/common-issues")
async def add_common_issue(request: CommonIssueRequest):
    """Add a common issue to the knowledge base"""
    try:
        reviewer.add_common_issue(
            request.issue,
            request.category,
            request.metadata
        )
        return {
            "status": "success",
            "message": "Common issue added",
            "total_count": reviewer.common_issues.count()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


from github_auth import (
    generate_oauth_url,
    exchange_code_for_token,
    get_user_repos,
    get_repo_pull_requests
)


# OAuth endpoints
@app.get("/auth/github")
async def github_oauth_init():
    """Initialize GitHub OAuth flow"""
    return generate_oauth_url()


@app.post("/auth/github/callback")
async def github_oauth_callback(code: str, state: str):
    """Handle GitHub OAuth callback"""
    try:
        result = exchange_code_for_token(code, state)
        return {
            "status": "success",
            "user": result
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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
    return {
        "status": "success",
        "last_analysis": reviewer.last_analysis_results,
        "analysis_details": {
            "codebase_issues": len(reviewer.last_analysis_results.get('codebase_issues', [])),
            "pattern_issues": len(reviewer.last_analysis_results.get('pattern_issues', [])),
            "type_issues": len(reviewer.last_analysis_results.get('type_issues', [])),
            "duplicate_issues": len(reviewer.last_analysis_results.get('duplicate_issues', [])),
            "total_verified": reviewer.last_analysis_results.get('total_issues', 0)
        }
    }


@app.get("/codebase-info")
async def get_codebase_info():
    """Get information about the analyzed codebase"""
    if not reviewer.codebase_analyzer.is_analyzed:
        raise HTTPException(status_code=404, detail="Codebase not analyzed. Run analysis first.")

    return {
        "analyzed": True,
        "files": len(reviewer.codebase_analyzer.all_files),
        "functions": len(reviewer.codebase_analyzer.all_functions),
        "dependencies": len(reviewer.codebase_analyzer.dependency_graph),
        "sample_files": list(reviewer.codebase_analyzer.all_files.keys())[:10]
    }


@app.post("/analyze-function/{function_name}")
async def analyze_function_impact(function_name: str, file_path: str = None):
    """Get detailed impact analysis for a specific function"""
    try:
        if not file_path:
            matching_functions = []
            for func_key in reviewer.codebase_analyzer.all_functions.keys():
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

        impact_analysis = reviewer.codebase_analyzer.get_function_impact_chain(func_key)
        dependency_analysis = reviewer.codebase_analyzer.analyze_function_dependencies(func_key)

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


async def analyze_github_repo_background(job_id: str, repo_url: str, branch: str, files_pattern: str):
    """Background task to analyze GitHub repository with REAL progress tracking"""
    print(f"\n{'=' * 80}")
    print(f"🚀 STARTING ANALYSIS JOB: {job_id}")
    print(f"{'=' * 80}\n")

    try:
        # Stage 1: Cloning (0-15%)
        update_job_status(job_id, status="running", progress=5, current_task="Cloning repository...")
        await asyncio.sleep(0.5)  # Let frontend see this update

        repo_dir = clone_github_repo(repo_url, branch)
        print(f"✅ Repo cloned to: {repo_dir}")

        # Stage 2: Scanning (15-25%)
        update_job_status(job_id, progress=15, current_task="Scanning files...")
        await asyncio.sleep(0.3)

        matching_files = []
        for pattern in files_pattern.split(","):
            pattern = pattern.strip()
            for file_path in Path(repo_dir).rglob(pattern):
                if file_path.is_file() and file_path.stat().st_size < 1024 * 1024:
                    matching_files.append(file_path)

        print(f"📁 Found {len(matching_files)} files")
        update_job_status(
            job_id,
            progress=25,
            current_task=f"Found {len(matching_files)} files",
            total_files=len(matching_files)
        )
        await asyncio.sleep(0.3)

        # Stage 3: Building graph (25-35%)
        is_large_repo = len(matching_files) > 100
        update_job_status(job_id, progress=30, current_task="Building codebase graph...")
        await asyncio.sleep(0.3)

        analysis_reviewer = CodeReviewer(
            openai_api_key=api_key,
            skip_duplicate_detection=is_large_repo
        )

        try:
            analysis_reviewer.enable_codebase_analysis(repo_dir)
            print("✅ Codebase graph built")
        except Exception as e:
            print(f"⚠️ Graph build warning: {e}")

        update_job_status(job_id, progress=35, current_task="Starting file analysis...")
        await asyncio.sleep(0.3)

        # Stage 4: Analyze files (35-95%)
        all_results = []
        successful_files = 0
        failed_files = 0

        for i, file_path in enumerate(matching_files):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    code = f.read()

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

                # Add small delay so progress is visible
                await asyncio.sleep(0.2)

                # Analyze
                review = analysis_reviewer.review_code(
                    code=code,
                    language="python",
                    file_path=str(file_path),
                    context=f"GitHub repo: {repo_url}"
                )

                if "error" not in review:
                    all_results.append({
                        "file_path": rel_path,
                        "review": review
                    })
                    successful_files += 1
                    print(f"✅ {len(review.get('issues', []))} issues found")
                else:
                    failed_files += 1
                    print(f"❌ Error: {review.get('error')}")

            except Exception as e:
                failed_files += 1
                print(f"❌ Exception: {e}")
                continue

        # Stage 5: Finalizing (95-100%)
        update_job_status(job_id, progress=95, current_task="Finalizing results...")
        await asyncio.sleep(0.5)

        total_issues = sum(len(r["review"].get("issues", [])) for r in all_results)

        results = {
            "repository": repo_url,
            "branch": branch,
            "files_analyzed": successful_files,
            "total_files_attempted": len(matching_files),
            "files_failed": failed_files,
            "total_issues": total_issues,
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
        shutil.rmtree(repo_dir, ignore_errors=True)
        del analysis_reviewer
        gc.collect()

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        update_job_status(
            job_id,
            status="failed",
            current_task=f"Error: {str(e)[:100]}",
            error=str(e)
        )

        # Cleanup on error
        try:
            if 'repo_dir' in locals() and os.path.exists(repo_dir):
                shutil.rmtree(repo_dir, ignore_errors=True)
            if 'analysis_reviewer' in locals():
                del analysis_reviewer
            gc.collect()
        except:
            pass


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
            request.files_pattern
        )

        # Generate shareable URL
        share_url = f"http://localhost:3000/share/{job_id}"  # Change to your domain

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
        host="0.0.0.0",
        port=8000,
        reload=True
    )
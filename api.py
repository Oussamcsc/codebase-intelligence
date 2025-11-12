"""
FastAPI REST API for Enhanced Modular Code Review Assistant
"""

import os
# Set environment variables to prevent multiprocessing/tokenizer warnings and improve stability
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
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

app = FastAPI(
    title="Enhanced Modular AI Code Review API",
    description="Comprehensive code review with codebase analysis, pattern matching, type checking, and duplicate detection",
    version="2.0.0"
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


# Initialize on startup
@app.on_event("startup")
async def startup_event():
    """Initialize knowledge base and codebase analysis on startup"""
    try:
        print("🚀 Initializing Enhanced Code Review System...")
        reviewer.initialize_knowledge_base()
        print("✅ Knowledge base initialized")
        
        # Enable codebase analysis for current directory
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
    

class JobStatusResponse(BaseModel):
    job_id: str
    status: str  # "pending", "running", "completed", "failed"
    progress: int  # 0-100
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
        "version": "2.0.0",
        "description": "Comprehensive code analysis with 4 specialized analyzers",
        "analyzers": [
            "Codebase Analyzer (dependencies, dead code, impact)",
            "Pattern Matcher (AST antipatterns, complexity)",
            "Type Analyzer (signatures, type hints)",
            "Duplicate Detector (code duplication)"
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
        "analyzers": {
            "codebase_analyzer": "✅ Active",
            "pattern_matcher": "✅ Active", 
            "type_analyzer": "✅ Active",
            "duplicate_detector": "✅ Active"
        },
        "knowledge_base": {
            "best_practices": reviewer.best_practices.count(),
            "common_issues": reviewer.common_issues.count()
        }
    }


@app.get("/stats")
async def get_stats():
    """Get comprehensive system statistics"""
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
        }
    }


@app.post("/review")
async def review_code(request: CodeReviewRequest):
    """
    Comprehensive code review with all analyzers

    Args:
        request: CodeReviewRequest with code, language, file_path, and optional context

    Returns:
        Comprehensive code review results with issues from all analyzers
    """
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
    """
    Review a file by path with full codebase analysis
    
    Args:
        request: FileReviewRequest with file_path and optional context
        
    Returns:
        Comprehensive code review results
    """
    try:
        file_path = Path(request.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")
            
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
            
        review = reviewer.review_code(
            code=code,
            language="python",  # Could be detected from file extension
            file_path=request.file_path,
            context=request.context
        )
        
        return review
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload-review")
async def upload_and_review(file: UploadFile = File(...), context: Optional[str] = None):
    """
    Upload a file and perform comprehensive review
    
    Args:
        file: Uploaded file
        context: Optional context string
        
    Returns:
        Comprehensive code review results
    """
    try:
        # Read uploaded file
        content = await file.read()
        code = content.decode('utf-8')
        
        # Save temporarily for file-based analysis
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
            # Clean up temp file
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
            # Try to find function across all files
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


# Storage for background jobs
job_storage = {}


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast_job_progress(self, job_id: str, progress: dict):
        message = json.dumps({"job_id": job_id, **progress})
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()


# Helper functions
def clone_github_repo(repo_url: str, branch: str = "main") -> str:
    """Clone GitHub repo to temporary directory"""
    temp_dir = tempfile.mkdtemp(prefix="code-review-")
    try:
        # Clone the repository
        subprocess.run([
            "git", "clone", "--depth", "1", "--branch", branch, 
            repo_url, temp_dir
        ], check=True, capture_output=True, text=True)
        return temp_dir
    except subprocess.CalledProcessError as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=f"Failed to clone repository: {e.stderr}")


async def analyze_github_repo_background(job_id: str, repo_url: str, branch: str, files_pattern: str):
    """Background task to analyze GitHub repository"""
    try:
        # Update job status
        job_storage[job_id]["status"] = "running"
        job_storage[job_id]["current_task"] = "Cloning repository..."
        job_storage[job_id]["progress"] = 10
        
        # Clone repository
        repo_dir = clone_github_repo(repo_url, branch)
        
        job_storage[job_id]["current_task"] = "Scanning files..."
        job_storage[job_id]["progress"] = 20
        
        # Find matching files
        matching_files = []
        for pattern in files_pattern.split(","):
            pattern = pattern.strip()
            for file_path in Path(repo_dir).rglob(pattern):
                if file_path.is_file() and file_path.stat().st_size < 1024 * 1024:  # Max 1MB per file
                    matching_files.append(file_path)
        
        job_storage[job_id]["total_files"] = len(matching_files)
        
        # Repository size warning and analysis strategy
        is_large_repo = len(matching_files) > 100
        if is_large_repo:
            print(f"⚠️ Large repository detected: {len(matching_files)} Python files")
            print("🚀 Using memory-optimized analysis (skipping duplicate detection)")
            job_storage[job_id]["current_task"] = f"Large repo detected ({len(matching_files)} files) - using memory-optimized analysis..."
        else:
            job_storage[job_id]["current_task"] = "Analyzing code..."
        
        # Create a specialized reviewer for this analysis
        analysis_reviewer = CodeReviewer(
            openai_api_key=api_key,
            skip_duplicate_detection=is_large_repo
        )
        job_storage[job_id]["progress"] = 30
        
        # Enable codebase analysis with timeout protection
        print("🔍 Building codebase graph...")
        try:
            analysis_reviewer.enable_codebase_analysis(repo_dir)
            print("✅ Codebase graph built successfully")
        except Exception as e:
            print(f"⚠️ Codebase graph building failed: {e}")
            print("📄 Continuing with file-by-file analysis only...")
            # Continue without codebase analysis
        
        all_results = []
        successful_files = 0
        failed_files = 0
        
        for i, file_path in enumerate(matching_files):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    code = f.read()
                
                # Get relative path for cleaner display (macOS symlink-safe)
                try:
                    resolved_file = Path(os.path.realpath(file_path))
                    resolved_repo = Path(os.path.realpath(repo_dir))
                    rel_path = str(resolved_file.relative_to(resolved_repo))
                except ValueError:
                    # Fallback if relative_to fails
                    rel_path = str(file_path.relative_to(repo_dir)) if str(file_path).startswith(str(repo_dir)) else file_path.name
                
                print(f"📄 Analyzing file {i+1}/{len(matching_files)}: {rel_path}")
                
                # Review the file
                review = analysis_reviewer.review_code(
                    code=code,
                    language="python",
                    file_path=str(file_path),
                    context=f"GitHub repo analysis: {repo_url}"
                )
                
                if "error" not in review:
                    all_results.append({
                        "file_path": rel_path,
                        "review": review
                    })
                    successful_files += 1
                    print(f"✅ Successfully analyzed {rel_path}: {len(review.get('issues', []))} issues found")
                else:
                    failed_files += 1
                    print(f"❌ Analysis returned error for {rel_path}: {review.get('error', 'Unknown error')}")
                
                # Update progress
                progress = 30 + int((i + 1) / len(matching_files) * 60)
                job_storage[job_id]["progress"] = progress
                job_storage[job_id]["files_analyzed"] = i + 1
                job_storage[job_id]["current_task"] = f"Analyzed {rel_path} ({successful_files} success, {failed_files} failed)"
                
            except Exception as e:
                failed_files += 1
                # Get relative path for error display (macOS symlink-safe)
                try:
                    resolved_file = Path(os.path.realpath(file_path))
                    resolved_repo = Path(os.path.realpath(repo_dir))
                    rel_path = str(resolved_file.relative_to(resolved_repo))
                except (ValueError, AttributeError):
                    # Fallback if relative_to fails or path is not relative
                    rel_path = str(file_path)
                print(f"❌ Exception analyzing {rel_path}: {e}")
                job_storage[job_id]["current_task"] = f"Error on {rel_path}: {str(e)[:50]}..."
                continue
        
        # Compile final results
        total_issues = sum(len(result["review"].get("issues", [])) for result in all_results)
        
        # Always complete the job, even with partial failures
        completion_status = "completed" if failed_files == 0 else "completed_with_errors"
        
        print(f"🏁 Analysis complete!")
        print(f"   📊 Files processed: {successful_files}/{len(matching_files)} successful")
        print(f"   📊 Total issues found: {total_issues}")
        print(f"   📊 Failed files: {failed_files}")
        
        job_storage[job_id]["status"] = "completed"  # Always mark as completed for frontend
        job_storage[job_id]["progress"] = 100
        job_storage[job_id]["current_task"] = f"Analysis complete: {successful_files}/{len(matching_files)} files processed"
        job_storage[job_id]["results"] = {
            "repository": repo_url,
            "branch": branch,
            "files_analyzed": successful_files,
            "total_files_attempted": len(matching_files),
            "files_failed": failed_files,
            "total_issues": total_issues,
            "results": all_results,
            "completion_status": completion_status
        }
        job_storage[job_id]["results_available"] = True
        
        # Cleanup
        print(f"🧹 Cleaning up temporary directory: {repo_dir}")
        shutil.rmtree(repo_dir, ignore_errors=True)
        
        # Memory cleanup to prevent leaks
        del analysis_reviewer
        gc.collect()
        print(f"🔧 Memory cleanup completed")
        
    except Exception as e:
        print(f"❌ Critical error in background job {job_id}: {e}")
        print(f"❌ Exception type: {type(e).__name__}")
        
        job_storage[job_id]["status"] = "failed"
        job_storage[job_id]["current_task"] = f"Critical error: {str(e)[:100]}"
        job_storage[job_id]["progress"] = 0
        job_storage[job_id]["results"] = {
            "error": str(e),
            "error_type": type(e).__name__,
            "repository": repo_url,
            "branch": branch
        }
        job_storage[job_id]["results_available"] = True
        
        # Cleanup on error
        try:
            if 'repo_dir' in locals() and os.path.exists(repo_dir):
                print(f"🧹 Cleaning up after error: {repo_dir}")
                shutil.rmtree(repo_dir, ignore_errors=True)
            
            # Memory cleanup on error
            if 'analysis_reviewer' in locals():
                del analysis_reviewer
            gc.collect()
            print(f"🔧 Error cleanup completed")
        except Exception as cleanup_error:
            print(f"⚠️ Could not cleanup {repo_dir}: {cleanup_error}")


@app.post("/github/analyze", response_model=AnalysisJobResponse)
async def analyze_github_repo(request: GitHubRepoRequest, background_tasks: BackgroundTasks):
    """
    Start analysis of a GitHub repository
    
    Args:
        request: GitHubRepoRequest with repo URL, branch, and file patterns
        
    Returns:
        Job ID and status for tracking the analysis
    """
    try:
        job_id = str(uuid.uuid4())
        
        # Initialize job status
        job_storage[job_id] = {
            "status": "pending",
            "progress": 0,
            "current_task": "Initializing...",
            "files_analyzed": 0,
            "total_files": 0,
            "results_available": False,
            "repository": request.repo_url,
            "branch": request.branch
        }
        
        # Start background analysis
        background_tasks.add_task(
            analyze_github_repo_background,
            job_id,
            request.repo_url,
            request.branch,
            request.files_pattern
        )
        
        return AnalysisJobResponse(
            job_id=job_id,
            status="pending",
            message="Analysis started. Use /github/status/{job_id} to track progress."
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/github/status/{job_id}", response_model=JobStatusResponse)
async def get_analysis_status(job_id: str):
    """Get status of a GitHub repository analysis job"""
    if job_id not in job_storage:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = job_storage[job_id]
    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        current_task=job["current_task"],
        files_analyzed=job["files_analyzed"],
        total_files=job["total_files"],
        results_available=job["results_available"]
    )


@app.get("/github/results/{job_id}")
async def get_analysis_results(job_id: str):
    """Get results of a completed GitHub repository analysis"""
    if job_id not in job_storage:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = job_storage[job_id]
    
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Analysis not completed yet")
    
    if not job["results_available"]:
        raise HTTPException(status_code=404, detail="Results not available")
    
    return {
        "status": "success",
        "job_id": job_id,
        "results": job["results"]
    }


@app.websocket("/ws/progress/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time progress updates"""
    await manager.connect(websocket)
    try:
        while True:
            if job_id in job_storage:
                job = job_storage[job_id]
                await websocket.send_text(json.dumps({
                    "job_id": job_id,
                    "status": job["status"],
                    "progress": job["progress"],
                    "current_task": job["current_task"],
                    "files_analyzed": job["files_analyzed"],
                    "total_files": job["total_files"]
                }))
                
                if job["status"] in ["completed", "failed"]:
                    break
            
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.delete("/github/jobs/{job_id}")
async def cleanup_job(job_id: str):
    """Clean up a finished job"""
    if job_id not in job_storage:
        raise HTTPException(status_code=404, detail="Job not found")
    
    del job_storage[job_id]
    return {"status": "success", "message": "Job cleaned up"}


if __name__ == "__main__":
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
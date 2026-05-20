"""Centralized environment configuration for the Codebase Intelligence backend."""

import os
from dotenv import load_dotenv

load_dotenv()

# API credentials
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")

# Server URLs
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
REDIRECT_URI = f"{BACKEND_URL}/auth/github/callback"
FRONTEND_REDIRECT_BASE = FRONTEND_URL
OAUTH_COOKIE_SECURE = BACKEND_URL.startswith("https://")

# Runtime settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
DB_PATH = os.getenv("DB_PATH", "code_review_results.db")

# Vector database / model settings
VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "./chroma_db")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

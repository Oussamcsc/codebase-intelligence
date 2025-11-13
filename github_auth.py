"""
GitHub OAuth Integration
Handles authentication and token management
"""

import os
import requests
from fastapi import HTTPException
from typing import Dict, Optional
import secrets

# Store active tokens (in production: use Redis/DB)
active_tokens: Dict[str, str] = {}
state_tokens: Dict[str, str] = {}

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
GITHUB_REDIRECT_URI = os.getenv("GITHUB_REDIRECT_URI", "http://localhost:3000/auth/callback")


def generate_oauth_url() -> Dict[str, str]:
    """Generate GitHub OAuth URL with state token"""
    state = secrets.token_urlsafe(32)
    state_tokens[state] = "pending"

    oauth_url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}"
        f"&redirect_uri={GITHUB_REDIRECT_URI}"
        f"&scope=repo,read:org"
        f"&state={state}"
    )

    return {
        "oauth_url": oauth_url,
        "state": state
    }


def exchange_code_for_token(code: str, state: str) -> Dict[str, str]:
    """Exchange OAuth code for access token"""

    # Verify state
    if state not in state_tokens:
        raise HTTPException(status_code=400, detail="Invalid state token")

    # Exchange code for token
    response = requests.post(
        "https://github.com/login/oauth/access_token",
        headers={"Accept": "application/json"},
        data={
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": GITHUB_REDIRECT_URI
        }
    )

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to exchange code for token")

    data = response.json()

    if "error" in data:
        raise HTTPException(status_code=400, detail=data.get("error_description", "OAuth error"))

    access_token = data["access_token"]

    # Get user info
    user_response = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"token {access_token}"}
    )

    user_data = user_response.json()
    username = user_data.get("login")

    # Store token (keyed by username)
    active_tokens[username] = access_token

    # Clean up state
    del state_tokens[state]

    return {
        "username": username,
        "avatar_url": user_data.get("avatar_url"),
        "access_token": access_token  # Frontend will store this
    }


def get_user_repos(access_token: str, page: int = 1, per_page: int = 30) -> list:
    """Get user's repositories"""

    response = requests.get(
        "https://api.github.com/user/repos",
        headers={"Authorization": f"token {access_token}"},
        params={
            "page": page,
            "per_page": per_page,
            "sort": "updated",
            "affiliation": "owner,collaborator"
        }
    )

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch repositories")

    repos = response.json()

    return [
        {
            "id": repo["id"],
            "name": repo["name"],
            "full_name": repo["full_name"],
            "description": repo.get("description"),
            "url": repo["html_url"],
            "clone_url": repo["clone_url"],
            "default_branch": repo.get("default_branch", "main"),
            "language": repo.get("language"),
            "updated_at": repo["updated_at"],
            "stars": repo["stargazers_count"]
        }
        for repo in repos
    ]


def get_repo_pull_requests(access_token: str, repo_full_name: str, state: str = "open") -> list:
    """Get pull requests for a repository"""

    response = requests.get(
        f"https://api.github.com/repos/{repo_full_name}/pulls",
        headers={"Authorization": f"token {access_token}"},
        params={"state": state}
    )

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch pull requests")

    prs = response.json()

    return [
        {
            "number": pr["number"],
            "title": pr["title"],
            "state": pr["state"],
            "user": pr["user"]["login"],
            "created_at": pr["created_at"],
            "updated_at": pr["updated_at"],
            "head_branch": pr["head"]["ref"],
            "base_branch": pr["base"]["ref"]
        }
        for pr in prs
    ]
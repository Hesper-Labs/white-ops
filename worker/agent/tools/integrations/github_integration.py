"""GitHub integration tool - manage issues, PRs, repos, and files."""

import json
import os
from typing import Any

import httpx

from agent.tools.base import BaseTool


class GitHubTool(BaseTool):
    name = "github"
    description = (
        "Interact with GitHub repositories. Create and list issues, "
        "create pull requests, list repos, and read file contents."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create_issue", "list_issues", "create_pr", "list_repos", "get_file"],
                "description": "The GitHub action to perform",
            },
            "owner": {
                "type": "string",
                "description": "Repository owner (user or org)",
            },
            "repo": {
                "type": "string",
                "description": "Repository name",
            },
            "title": {
                "type": "string",
                "description": "Issue or PR title",
            },
            "body": {
                "type": "string",
                "description": "Issue/PR body or description",
            },
            "labels": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Labels for the issue",
            },
            "head": {
                "type": "string",
                "description": "PR head branch",
            },
            "base": {
                "type": "string",
                "description": "PR base branch (default: main)",
            },
            "path": {
                "type": "string",
                "description": "File path within the repo for get_file",
            },
            "ref": {
                "type": "string",
                "description": "Branch or commit ref (default: main)",
            },
            "state": {
                "type": "string",
                "enum": ["open", "closed", "all"],
                "description": "Issue state filter (default: open)",
            },
            "per_page": {
                "type": "integer",
                "description": "Results per page (default 30, max 100)",
            },
        },
        "required": ["action"],
    }

    API_BASE = "https://api.github.com"

    def _get_token(self) -> str:
        token = os.environ.get("GITHUB_TOKEN", "")
        if not token:
            raise ValueError("GITHUB_TOKEN environment variable is not set")
        return token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]

        try:
            if action == "create_issue":
                return await self._create_issue(kwargs)
            elif action == "list_issues":
                return await self._list_issues(kwargs)
            elif action == "create_pr":
                return await self._create_pr(kwargs)
            elif action == "list_repos":
                return await self._list_repos(kwargs)
            elif action == "get_file":
                return await self._get_file(kwargs)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except ValueError as e:
            return json.dumps({"error": str(e)})
        except httpx.HTTPError as e:
            return json.dumps({"error": f"GitHub API request failed: {e}"})

    def _require_repo(self, kwargs: dict) -> tuple[str, str]:
        owner = kwargs.get("owner")
        repo = kwargs.get("repo")
        if not owner or not repo:
            raise ValueError("owner and repo are required")
        return owner, repo

    async def _create_issue(self, kwargs: dict) -> str:
        owner, repo = self._require_repo(kwargs)
        title = kwargs.get("title")
        if not title:
            return json.dumps({"error": "title is required"})

        payload: dict[str, Any] = {"title": title}
        if kwargs.get("body"):
            payload["body"] = kwargs["body"]
        if kwargs.get("labels"):
            payload["labels"] = kwargs["labels"]

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.API_BASE}/repos/{owner}/{repo}/issues",
                headers=self._headers(),
                json=payload,
            )
            if resp.status_code == 201:
                data = resp.json()
                return json.dumps({
                    "success": True,
                    "number": data["number"],
                    "html_url": data["html_url"],
                    "title": data["title"],
                })
            return json.dumps({"error": f"Status {resp.status_code}", "body": resp.text[:500]})

    async def _list_issues(self, kwargs: dict) -> str:
        owner, repo = self._require_repo(kwargs)
        state = kwargs.get("state", "open")
        per_page = min(kwargs.get("per_page", 30), 100)

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.API_BASE}/repos/{owner}/{repo}/issues",
                headers=self._headers(),
                params={"state": state, "per_page": per_page},
            )
            if resp.status_code != 200:
                return json.dumps({"error": f"Status {resp.status_code}", "body": resp.text[:500]})

            issues = [
                {
                    "number": issue["number"],
                    "title": issue["title"],
                    "state": issue["state"],
                    "user": issue["user"]["login"],
                    "labels": [l["name"] for l in issue.get("labels", [])],
                    "created_at": issue["created_at"],
                    "html_url": issue["html_url"],
                }
                for issue in resp.json()
                if "pull_request" not in issue  # exclude PRs
            ]
            return json.dumps({"issues": issues, "count": len(issues)})

    async def _create_pr(self, kwargs: dict) -> str:
        owner, repo = self._require_repo(kwargs)
        title = kwargs.get("title")
        head = kwargs.get("head")
        if not title or not head:
            return json.dumps({"error": "title and head branch are required"})

        payload: dict[str, Any] = {
            "title": title,
            "head": head,
            "base": kwargs.get("base", "main"),
        }
        if kwargs.get("body"):
            payload["body"] = kwargs["body"]

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.API_BASE}/repos/{owner}/{repo}/pulls",
                headers=self._headers(),
                json=payload,
            )
            if resp.status_code == 201:
                data = resp.json()
                return json.dumps({
                    "success": True,
                    "number": data["number"],
                    "html_url": data["html_url"],
                    "title": data["title"],
                    "state": data["state"],
                })
            return json.dumps({"error": f"Status {resp.status_code}", "body": resp.text[:500]})

    async def _list_repos(self, kwargs: dict) -> str:
        owner = kwargs.get("owner")
        per_page = min(kwargs.get("per_page", 30), 100)

        async with httpx.AsyncClient(timeout=15) as client:
            if owner:
                url = f"{self.API_BASE}/users/{owner}/repos"
            else:
                url = f"{self.API_BASE}/user/repos"

            resp = await client.get(
                url,
                headers=self._headers(),
                params={"per_page": per_page, "sort": "updated"},
            )
            if resp.status_code != 200:
                return json.dumps({"error": f"Status {resp.status_code}", "body": resp.text[:500]})

            repos = [
                {
                    "name": r["name"],
                    "full_name": r["full_name"],
                    "description": r.get("description", ""),
                    "private": r["private"],
                    "language": r.get("language"),
                    "html_url": r["html_url"],
                    "updated_at": r["updated_at"],
                }
                for r in resp.json()
            ]
            return json.dumps({"repos": repos, "count": len(repos)})

    async def _get_file(self, kwargs: dict) -> str:
        owner, repo = self._require_repo(kwargs)
        path = kwargs.get("path")
        if not path:
            return json.dumps({"error": "path is required"})

        ref = kwargs.get("ref", "main")

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.API_BASE}/repos/{owner}/{repo}/contents/{path}",
                headers=self._headers(),
                params={"ref": ref},
            )
            if resp.status_code != 200:
                return json.dumps({"error": f"Status {resp.status_code}", "body": resp.text[:500]})

            data = resp.json()
            import base64

            content = ""
            if data.get("encoding") == "base64" and data.get("content"):
                try:
                    content = base64.b64decode(data["content"]).decode("utf-8")
                except Exception:
                    content = "[binary file - cannot decode as text]"

            return json.dumps({
                "name": data["name"],
                "path": data["path"],
                "size": data["size"],
                "sha": data["sha"],
                "content": content[:10000],
                "html_url": data.get("html_url", ""),
            })

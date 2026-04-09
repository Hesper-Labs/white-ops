"""CI/CD pipeline tool - interact with GitHub Actions workflows."""

import json
import os
from typing import Any

import httpx
import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

MAX_OUTPUT_BYTES = 50 * 1024
GITHUB_API_BASE = "https://api.github.com"


def _truncate(text: str) -> str:
    if len(text) > MAX_OUTPUT_BYTES:
        return text[:MAX_OUTPUT_BYTES] + "\n... [output truncated]"
    return text


class CICDTool(BaseTool):
    name = "ci_cd"
    description = (
        "Interact with GitHub Actions CI/CD pipelines. Trigger workflows, "
        "check status, list runs, download artifacts, and cancel runs. "
        "Requires GITHUB_TOKEN environment variable."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "trigger_workflow", "get_workflow_status", "list_runs",
                    "download_artifact", "cancel_run",
                ],
                "description": "CI/CD action to perform.",
            },
            "repo": {
                "type": "string",
                "description": "GitHub repository (owner/repo format).",
            },
            "workflow": {
                "type": "string",
                "description": "Workflow filename or ID (for trigger_workflow, list_runs).",
            },
            "ref": {
                "type": "string",
                "description": "Git ref (branch/tag) to trigger workflow on. Default: main.",
            },
            "inputs": {
                "type": "object",
                "description": "Workflow dispatch inputs.",
                "additionalProperties": {"type": "string"},
            },
            "run_id": {
                "type": "integer",
                "description": "Workflow run ID (for get_workflow_status, download_artifact, cancel_run).",
            },
            "status": {
                "type": "string",
                "enum": ["queued", "in_progress", "completed", "waiting", "requested"],
                "description": "Filter runs by status (for list_runs).",
            },
            "artifact_name": {
                "type": "string",
                "description": "Artifact name (for download_artifact).",
            },
            "output_path": {
                "type": "string",
                "description": "Output file path (for download_artifact).",
            },
        },
        "required": ["action", "repo"],
    }

    def _get_token(self) -> str | None:
        return os.environ.get("GITHUB_TOKEN")

    def _headers(self, token: str) -> dict:
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action")
        repo = kwargs.get("repo", "")
        logger.info("cicd_execute", action=action, repo=repo)

        token = self._get_token()
        if not token:
            return json.dumps({"error": "GITHUB_TOKEN environment variable not set"})

        if not repo or "/" not in repo:
            return json.dumps({"error": "repo must be in owner/repo format"})

        try:
            if action == "trigger_workflow":
                return await self._trigger_workflow(kwargs, repo, token)
            elif action == "get_workflow_status":
                return await self._get_workflow_status(kwargs, repo, token)
            elif action == "list_runs":
                return await self._list_runs(kwargs, repo, token)
            elif action == "download_artifact":
                return await self._download_artifact(kwargs, repo, token)
            elif action == "cancel_run":
                return await self._cancel_run(kwargs, repo, token)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except httpx.TimeoutException:
            return json.dumps({"error": "GitHub API request timed out"})
        except httpx.HTTPStatusError as e:
            error_body = ""
            try:
                error_body = e.response.json().get("message", "")
            except Exception:
                error_body = e.response.text[:500]
            return json.dumps({"error": f"HTTP {e.response.status_code}: {error_body}"})
        except Exception as e:
            logger.error("cicd_error", error=str(e))
            return json.dumps({"error": f"CI/CD operation failed: {e}"})

    async def _trigger_workflow(self, kwargs: dict, repo: str, token: str) -> str:
        workflow = kwargs.get("workflow")
        if not workflow:
            return json.dumps({"error": "workflow is required"})

        ref = kwargs.get("ref", "main")
        inputs = kwargs.get("inputs", {})

        url = f"{GITHUB_API_BASE}/repos/{repo}/actions/workflows/{workflow}/dispatches"
        payload: dict[str, Any] = {"ref": ref}
        if inputs:
            payload["inputs"] = inputs

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=self._headers(token), json=payload)
            resp.raise_for_status()

        logger.info("cicd_workflow_triggered", repo=repo, workflow=workflow, ref=ref)
        return json.dumps({
            "success": True,
            "message": f"Workflow '{workflow}' triggered on {ref}",
            "repo": repo,
        })

    async def _get_workflow_status(self, kwargs: dict, repo: str, token: str) -> str:
        run_id = kwargs.get("run_id")
        if not run_id:
            return json.dumps({"error": "run_id is required"})

        url = f"{GITHUB_API_BASE}/repos/{repo}/actions/runs/{run_id}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self._headers(token))
            resp.raise_for_status()
            data = resp.json()

        result = {
            "id": data.get("id"),
            "name": data.get("name"),
            "status": data.get("status"),
            "conclusion": data.get("conclusion"),
            "html_url": data.get("html_url"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "head_branch": data.get("head_branch"),
            "head_sha": data.get("head_sha", "")[:8],
            "run_attempt": data.get("run_attempt"),
        }

        # Fetch jobs for this run
        jobs_url = f"{url}/jobs"
        async with httpx.AsyncClient(timeout=30) as client:
            jobs_resp = await client.get(jobs_url, headers=self._headers(token))
            if jobs_resp.status_code == 200:
                jobs_data = jobs_resp.json()
                result["jobs"] = [
                    {
                        "name": j.get("name"),
                        "status": j.get("status"),
                        "conclusion": j.get("conclusion"),
                        "started_at": j.get("started_at"),
                        "completed_at": j.get("completed_at"),
                    }
                    for j in jobs_data.get("jobs", [])
                ]

        return _truncate(json.dumps(result))

    async def _list_runs(self, kwargs: dict, repo: str, token: str) -> str:
        workflow = kwargs.get("workflow")
        status = kwargs.get("status")

        if workflow:
            url = f"{GITHUB_API_BASE}/repos/{repo}/actions/workflows/{workflow}/runs"
        else:
            url = f"{GITHUB_API_BASE}/repos/{repo}/actions/runs"

        params: dict[str, str] = {"per_page": "20"}
        if status:
            params["status"] = status

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self._headers(token), params=params)
            resp.raise_for_status()
            data = resp.json()

        runs = [
            {
                "id": r.get("id"),
                "name": r.get("name"),
                "status": r.get("status"),
                "conclusion": r.get("conclusion"),
                "head_branch": r.get("head_branch"),
                "created_at": r.get("created_at"),
                "html_url": r.get("html_url"),
            }
            for r in data.get("workflow_runs", [])
        ]

        logger.info("cicd_runs_listed", repo=repo, count=len(runs))
        return _truncate(json.dumps({"runs": runs, "total_count": data.get("total_count", 0)}))

    async def _download_artifact(self, kwargs: dict, repo: str, token: str) -> str:
        run_id = kwargs.get("run_id")
        artifact_name = kwargs.get("artifact_name")
        output_path = kwargs.get("output_path")

        if not run_id:
            return json.dumps({"error": "run_id is required"})
        if not artifact_name:
            return json.dumps({"error": "artifact_name is required"})
        if not output_path:
            return json.dumps({"error": "output_path is required"})

        # List artifacts for the run
        url = f"{GITHUB_API_BASE}/repos/{repo}/actions/runs/{run_id}/artifacts"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self._headers(token))
            resp.raise_for_status()
            data = resp.json()

        # Find the matching artifact
        artifact = None
        for a in data.get("artifacts", []):
            if a.get("name") == artifact_name:
                artifact = a
                break

        if not artifact:
            available = [a.get("name") for a in data.get("artifacts", [])]
            return json.dumps({
                "error": f"Artifact '{artifact_name}' not found",
                "available_artifacts": available,
            })

        # Download the artifact
        download_url = artifact["archive_download_url"]
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            resp = await client.get(download_url, headers=self._headers(token))
            resp.raise_for_status()

            from pathlib import Path
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(resp.content)

        logger.info("cicd_artifact_downloaded", artifact=artifact_name, path=output_path)
        return json.dumps({
            "success": True,
            "artifact_name": artifact_name,
            "output_path": output_path,
            "size_bytes": len(resp.content),
        })

    async def _cancel_run(self, kwargs: dict, repo: str, token: str) -> str:
        run_id = kwargs.get("run_id")
        if not run_id:
            return json.dumps({"error": "run_id is required"})

        url = f"{GITHUB_API_BASE}/repos/{repo}/actions/runs/{run_id}/cancel"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=self._headers(token))
            resp.raise_for_status()

        logger.info("cicd_run_cancelled", repo=repo, run_id=run_id)
        return json.dumps({"success": True, "run_id": run_id, "message": "Run cancelled"})

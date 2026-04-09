"""Git operations tool - clone, status, diff, log, commit, and branch management."""

import asyncio
import json
from typing import Any

from agent.tools.base import BaseTool


class GitOpsTool(BaseTool):
    name = "git_ops"
    description = (
        "Perform Git operations on repositories. Clone repos, check status, "
        "view diffs and logs, create commits, and list branches."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["clone", "status", "diff", "log", "commit", "branch_list"],
                "description": "The Git action to perform",
            },
            "repo_url": {
                "type": "string",
                "description": "Repository URL for clone",
            },
            "path": {
                "type": "string",
                "description": "Local repository path (working directory for git commands)",
            },
            "message": {
                "type": "string",
                "description": "Commit message for commit action",
            },
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Files to stage before commit (default: all changed files)",
            },
            "branch": {
                "type": "string",
                "description": "Branch name for clone --branch",
            },
            "max_count": {
                "type": "integer",
                "description": "Number of log entries to show (default 10)",
            },
            "target": {
                "type": "string",
                "description": "Target for diff (file path, branch, or commit)",
            },
        },
        "required": ["action"],
    }

    async def _run_git(self, args: list[str], cwd: str | None = None) -> tuple[int, str, str]:
        """Run a git command and return (returncode, stdout, stderr)."""
        proc = await asyncio.create_subprocess_exec(
            "git", *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        return (
            proc.returncode or 0,
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
        )

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]
        path = kwargs.get("path")

        try:
            if action == "clone":
                return await self._clone(kwargs)
            elif action == "status":
                return await self._status(path)
            elif action == "diff":
                return await self._diff(path, kwargs)
            elif action == "log":
                return await self._log(path, kwargs)
            elif action == "commit":
                return await self._commit(path, kwargs)
            elif action == "branch_list":
                return await self._branch_list(path)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except TimeoutError:
            return json.dumps({"error": "Git command timed out after 60 seconds"})
        except FileNotFoundError:
            return json.dumps({"error": "git executable not found"})

    async def _clone(self, kwargs: dict) -> str:
        repo_url = kwargs.get("repo_url")
        if not repo_url:
            return json.dumps({"error": "repo_url is required"})

        path = kwargs.get("path", ".")
        args = ["clone"]
        if kwargs.get("branch"):
            args.extend(["--branch", kwargs["branch"]])
        args.extend(["--depth", "1", repo_url, path])

        code, stdout, stderr = await self._run_git(args)
        if code == 0:
            return json.dumps({"success": True, "path": path, "output": stdout.strip()})
        return json.dumps({"error": stderr.strip() or stdout.strip()})

    async def _status(self, path: str | None) -> str:
        code, stdout, stderr = await self._run_git(
            ["status", "--porcelain", "--branch"], cwd=path
        )
        if code != 0:
            return json.dumps({"error": stderr.strip()})

        lines = stdout.strip().split("\n") if stdout.strip() else []
        branch_line = lines[0] if lines and lines[0].startswith("##") else ""
        file_lines = [l for l in lines if not l.startswith("##")]

        files = []
        for line in file_lines:
            if len(line) >= 4:
                status_code = line[:2].strip()
                file_path = line[3:]
                files.append({"status": status_code, "file": file_path})

        return json.dumps({
            "branch": branch_line.replace("## ", "") if branch_line else "unknown",
            "files": files,
            "clean": len(files) == 0,
        })

    async def _diff(self, path: str | None, kwargs: dict) -> str:
        args = ["diff", "--stat"]
        target = kwargs.get("target")
        if target:
            args.append(target)

        code, stdout, stderr = await self._run_git(args, cwd=path)
        if code != 0:
            return json.dumps({"error": stderr.strip()})

        # Also get full diff (truncated)
        full_args = ["diff"]
        if target:
            full_args.append(target)

        _, full_stdout, _ = await self._run_git(full_args, cwd=path)

        return json.dumps({
            "stat": stdout.strip(),
            "diff": full_stdout[:8000],
            "truncated": len(full_stdout) > 8000,
        })

    async def _log(self, path: str | None, kwargs: dict) -> str:
        max_count = kwargs.get("max_count", 10)
        code, stdout, stderr = await self._run_git(
            ["log", f"--max-count={max_count}", "--pretty=format:%H|%an|%ae|%ai|%s"],
            cwd=path,
        )
        if code != 0:
            return json.dumps({"error": stderr.strip()})

        commits = []
        for line in stdout.strip().split("\n"):
            if "|" in line:
                parts = line.split("|", 4)
                if len(parts) == 5:
                    commits.append({
                        "hash": parts[0][:8],
                        "full_hash": parts[0],
                        "author": parts[1],
                        "email": parts[2],
                        "date": parts[3],
                        "message": parts[4],
                    })
        return json.dumps({"commits": commits, "count": len(commits)})

    async def _commit(self, path: str | None, kwargs: dict) -> str:
        message = kwargs.get("message")
        if not message:
            return json.dumps({"error": "message is required"})

        files = kwargs.get("files")
        if files:
            for f in files:
                code, _, stderr = await self._run_git(["add", f], cwd=path)
                if code != 0:
                    return json.dumps({"error": f"Failed to stage {f}: {stderr.strip()}"})
        else:
            code, _, stderr = await self._run_git(["add", "-A"], cwd=path)
            if code != 0:
                return json.dumps({"error": f"Failed to stage files: {stderr.strip()}"})

        code, stdout, stderr = await self._run_git(
            ["commit", "-m", message], cwd=path
        )
        if code != 0:
            return json.dumps({"error": stderr.strip() or stdout.strip()})

        return json.dumps({"success": True, "output": stdout.strip()})

    async def _branch_list(self, path: str | None) -> str:
        code, stdout, stderr = await self._run_git(
            ["branch", "-a", "--format=%(refname:short)|%(objectname:short)|%(upstream:short)"],
            cwd=path,
        )
        if code != 0:
            return json.dumps({"error": stderr.strip()})

        branches = []
        for line in stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("|", 2)
                branches.append({
                    "name": parts[0] if len(parts) > 0 else "",
                    "commit": parts[1] if len(parts) > 1 else "",
                    "upstream": parts[2] if len(parts) > 2 else "",
                })

        # Get current branch
        _, current, _ = await self._run_git(["branch", "--show-current"], cwd=path)

        return json.dumps({
            "current": current.strip(),
            "branches": branches,
            "count": len(branches),
        })

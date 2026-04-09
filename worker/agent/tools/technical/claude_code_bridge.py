"""Claude Code CLI bridge tool - comprehensive integration with Claude Code.

Provides a unified interface to Claude Code's capabilities including task execution,
code review, refactoring, test generation, git workflows, and project scaffolding.
All operations run via the `claude` CLI as async subprocesses with proper timeouts,
rate limiting, and structured output.
"""

import asyncio
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_OUTPUT_BYTES = 100 * 1024  # 100 KB output cap
MAX_CONCURRENT = 10  # max concurrent claude processes

# Paths that must never be used as working directories or file targets
BLOCKED_PATH_PREFIXES = (
    "/",       # root itself
    "/etc",
    "/usr",
    "/bin",
    "/sbin",
    "/boot",
    "/dev",
    "/proc",
    "/sys",
    "/var/run",
    "/var/log",
    "/Library",
    "/System",
)

# Per-action timeout defaults (seconds)
ACTION_TIMEOUTS: dict[str, int] = {
    "run_task": 600,
    "plan": 300,
    "review_code": 300,
    "execute_command": 120,
    "generate_tests": 300,
    "refactor": 300,
    "fix_bug": 600,
    "generate_docs": 300,
    "git_workflow": 120,
    "dependency_audit": 180,
    "scaffold_project": 300,
    "multi_file_edit": 600,
}

VALID_ACTIONS = set(ACTION_TIMEOUTS)

# Allowed-tools presets per action to restrict what Claude Code can do
ALLOWED_TOOLS: dict[str, list[str]] = {
    "review_code": ["Read", "Grep", "Glob"],
    "generate_docs": ["Read", "Grep", "Glob", "Write"],
    "dependency_audit": ["Read", "Bash", "Glob"],
    "generate_tests": ["Read", "Grep", "Glob", "Write"],
}

# ---------------------------------------------------------------------------
# JSON Schema for parameters
# ---------------------------------------------------------------------------

_PARAMETERS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": sorted(VALID_ACTIONS),
            "description": "The action to perform via Claude Code.",
        },
        # --- run_task ---
        "task": {
            "type": "string",
            "description": "(run_task) Task description to send to Claude Code.",
        },
        # --- plan ---
        "description": {
            "type": "string",
            "description": (
                "(plan | fix_bug | scaffold_project) "
                "Description of what to plan, the bug to fix, or the project to scaffold."
            ),
        },
        # --- shared ---
        "working_directory": {
            "type": "string",
            "description": "Working directory for the Claude Code process.",
        },
        "file_path": {
            "type": "string",
            "description": (
                "(review_code | generate_tests | refactor | fix_bug | generate_docs) "
                "Path to the file or directory to operate on."
            ),
        },
        # --- review_code ---
        "review_type": {
            "type": "string",
            "enum": ["security", "performance", "quality", "all"],
            "default": "all",
            "description": "(review_code) Focus area for the code review.",
        },
        # --- execute_command ---
        "command": {
            "type": "string",
            "description": "(execute_command) Shell command to execute.",
        },
        # --- generate_tests ---
        "test_framework": {
            "type": "string",
            "enum": ["pytest", "jest", "vitest"],
            "default": "pytest",
            "description": "(generate_tests) Testing framework to target.",
        },
        # --- refactor ---
        "refactor_type": {
            "type": "string",
            "enum": ["extract_function", "rename", "simplify", "optimize", "dry"],
            "default": "simplify",
            "description": "(refactor) Type of refactoring to perform.",
        },
        # --- fix_bug ---
        "error_message": {
            "type": "string",
            "description": "(fix_bug) Optional error message or traceback to help diagnose the bug.",
        },
        # --- generate_docs ---
        "doc_type": {
            "type": "string",
            "enum": ["api", "readme", "inline", "architecture"],
            "default": "api",
            "description": "(generate_docs) Type of documentation to generate.",
        },
        # --- git_workflow ---
        "operation": {
            "type": "string",
            "enum": [
                "commit", "branch", "merge", "diff", "log",
                "pr_create", "pr_review",
            ],
            "description": "(git_workflow) Git operation to perform.",
        },
        # --- scaffold_project ---
        "project_type": {
            "type": "string",
            "enum": ["react", "fastapi", "node", "python"],
            "description": "(scaffold_project) Type of project to scaffold.",
        },
        "name": {
            "type": "string",
            "description": "(scaffold_project) Name for the new project.",
        },
        "features": {
            "type": "array",
            "items": {"type": "string"},
            "description": "(scaffold_project) List of features to include.",
        },
        # --- multi_file_edit ---
        "instructions": {
            "type": "string",
            "description": "(multi_file_edit) Instructions describing the coordinated edits.",
        },
        "file_paths": {
            "type": "array",
            "items": {"type": "string"},
            "description": "(multi_file_edit) List of file paths to edit.",
        },
        # --- optional overrides ---
        "timeout": {
            "type": "integer",
            "description": "Override default timeout (seconds). Capped at 900.",
        },
        "allowed_tools": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Override the default allowed-tools list for Claude Code.",
        },
    },
    "required": ["action"],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_path_blocked(path_str: str) -> bool:
    """Return True if the resolved path falls under a blocked prefix."""
    try:
        resolved = str(Path(path_str).resolve())
    except (OSError, ValueError):
        return True

    # Block the root directory itself
    if resolved == "/":
        return True

    for prefix in BLOCKED_PATH_PREFIXES:
        if prefix == "/":
            continue
        if resolved == prefix or resolved.startswith(prefix + "/"):
            return True

    return False


def _truncate(text: str, max_bytes: int = MAX_OUTPUT_BYTES) -> str:
    """Truncate text to at most *max_bytes* UTF-8 bytes."""
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode("utf-8", errors="replace") + "\n... [truncated]"


# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------

class ClaudeCodeBridgeTool(BaseTool):
    """Bridge to the Claude Code CLI for advanced development operations."""

    name = "claude_code"
    description = (
        "Execute development tasks via the Claude Code CLI. Supports: "
        "run_task, plan, review_code, execute_command, generate_tests, "
        "refactor, fix_bug, generate_docs, git_workflow, dependency_audit, "
        "scaffold_project, and multi_file_edit."
    )
    parameters = _PARAMETERS_SCHEMA

    def __init__(self) -> None:
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        self._claude_path: str | None = None  # resolved lazily

    # ------------------------------------------------------------------
    # Claude CLI resolution
    # ------------------------------------------------------------------

    async def _resolve_claude(self) -> str:
        """Find the ``claude`` binary, caching the result."""
        if self._claude_path is not None:
            return self._claude_path

        path = shutil.which("claude")
        if path is None:
            # Try common install locations
            for candidate in (
                os.path.expanduser("~/.claude/local/claude"),
                "/usr/local/bin/claude",
                os.path.expanduser("~/.local/bin/claude"),
            ):
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    path = candidate
                    break

        if path is None:
            raise FileNotFoundError(
                "Claude Code CLI ('claude') is not installed or not on PATH. "
                "Install it with: npm install -g @anthropic-ai/claude-code"
            )

        self._claude_path = path
        logger.info("claude_code.resolved", path=path)
        return path

    # ------------------------------------------------------------------
    # Low-level CLI runner
    # ------------------------------------------------------------------

    async def _run_claude(
        self,
        prompt: str,
        *,
        working_directory: str | None = None,
        timeout: int = 600,
        allowed_tools: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run the Claude Code CLI and return parsed output."""
        claude_bin = await self._resolve_claude()

        args = [claude_bin, "-p", prompt, "--output-format", "json"]

        if allowed_tools:
            args.extend(["--allowedTools", ",".join(allowed_tools)])

        cwd = working_directory or os.getcwd()

        log = logger.bind(cwd=cwd, timeout=timeout)
        log.info("claude_code.start", prompt_len=len(prompt))

        start = time.monotonic()

        async with self._semaphore:
            try:
                proc = await asyncio.create_subprocess_exec(
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    env={**os.environ, "CLAUDE_CODE_ENTRYPOINT": "white-ops-bridge"},
                )
                stdout_raw, stderr_raw = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except TimeoutError:
                log.warning("claude_code.timeout", timeout=timeout)
                try:
                    proc.kill()  # type: ignore[union-attr]
                    await proc.wait()  # type: ignore[union-attr]
                except Exception:
                    pass
                return {
                    "success": False,
                    "error": f"Claude Code timed out after {timeout}s",
                }
            except FileNotFoundError:
                return {
                    "success": False,
                    "error": "Claude Code CLI binary not found at expected path.",
                }
            except OSError as exc:
                log.error("claude_code.os_error", error=str(exc))
                return {"success": False, "error": f"OS error: {exc}"}

        elapsed = round(time.monotonic() - start, 2)
        stdout_str = _truncate(stdout_raw.decode("utf-8", errors="replace"))
        stderr_str = _truncate(
            stderr_raw.decode("utf-8", errors="replace"), MAX_OUTPUT_BYTES // 4
        )

        log.info(
            "claude_code.finished",
            exit_code=proc.returncode,
            duration=elapsed,
            stdout_len=len(stdout_str),
        )

        if proc.returncode != 0:
            return {
                "success": False,
                "error": stderr_str or f"claude exited with code {proc.returncode}",
                "stdout": stdout_str,
                "duration_seconds": elapsed,
            }

        # Try to parse JSON from stdout (Claude --output-format json)
        result_text = stdout_str
        try:
            parsed = json.loads(stdout_str)
            if isinstance(parsed, dict) and "result" in parsed:
                result_text = parsed["result"]
            elif isinstance(parsed, dict):
                result_text = json.dumps(parsed, indent=2)
            elif isinstance(parsed, str):
                result_text = parsed
        except (json.JSONDecodeError, TypeError):
            pass  # keep raw text

        return {
            "success": True,
            "result": result_text,
            "duration_seconds": elapsed,
        }

    # ------------------------------------------------------------------
    # Input validation helpers
    # ------------------------------------------------------------------

    def _validate_working_dir(self, wd: str | None) -> str | None:
        """Validate and return working directory, or an error string."""
        if wd is None:
            return None
        if _is_path_blocked(wd):
            return f"Blocked: working directory '{wd}' is in a restricted location."
        if not Path(wd).is_dir():
            return f"Working directory does not exist: {wd}"
        return None

    def _validate_file_path(self, fp: str) -> str | None:
        """Validate file path, return error string or None."""
        if _is_path_blocked(fp):
            return f"Blocked: file path '{fp}' is in a restricted location."
        p = Path(fp)
        if not p.exists():
            return f"Path does not exist: {fp}"
        return None

    def _read_file_safe(self, fp: str, max_bytes: int = MAX_OUTPUT_BYTES) -> str:
        """Read a file with size guard."""
        p = Path(fp)
        size = p.stat().st_size
        if size > max_bytes:
            return p.read_text(errors="replace")[:max_bytes] + "\n... [file truncated]"
        return p.read_text(errors="replace")

    # ------------------------------------------------------------------
    # Action dispatchers
    # ------------------------------------------------------------------

    async def execute(self, **kwargs: Any) -> Any:  # noqa: C901
        action: str = kwargs.get("action", "")
        if action not in VALID_ACTIONS:
            return json.dumps({
                "success": False,
                "action": action,
                "error": f"Unknown action '{action}'. Valid: {sorted(VALID_ACTIONS)}",
            })

        timeout = min(kwargs.get("timeout") or ACTION_TIMEOUTS[action], 900)
        user_tools = kwargs.get("allowed_tools")
        start_ts = time.monotonic()

        log = logger.bind(action=action)
        log.info("claude_code_bridge.dispatch")

        try:
            handler = getattr(self, f"_action_{action}", None)
            if handler is None:
                return json.dumps({
                    "success": False,
                    "action": action,
                    "error": "Handler not implemented.",
                })
            result: dict[str, Any] = await handler(
                kwargs, timeout=timeout, user_tools=user_tools,
            )
        except FileNotFoundError as exc:
            result = {"success": False, "error": str(exc)}
        except Exception as exc:
            log.error("claude_code_bridge.error", error=str(exc), exc_info=True)
            result = {"success": False, "error": f"Internal error: {exc}"}

        result.setdefault("action", action)
        result.setdefault("duration_seconds", round(time.monotonic() - start_ts, 2))
        result.setdefault("files_modified", [])

        return json.dumps(result, default=str)

    # ---- run_task ----

    async def _action_run_task(
        self, params: dict, *, timeout: int, user_tools: list[str] | None,
    ) -> dict[str, Any]:
        task = params.get("task")
        if not task:
            return {"success": False, "error": "Missing required parameter: task"}

        wd = params.get("working_directory")
        if err := self._validate_working_dir(wd):
            return {"success": False, "error": err}

        return await self._run_claude(
            task, working_directory=wd, timeout=timeout,
            allowed_tools=user_tools,
        )

    # ---- plan ----

    async def _action_plan(
        self, params: dict, *, timeout: int, user_tools: list[str] | None,
    ) -> dict[str, Any]:
        description = params.get("description")
        if not description:
            return {"success": False, "error": "Missing required parameter: description"}

        wd = params.get("working_directory")
        if err := self._validate_working_dir(wd):
            return {"success": False, "error": err}

        prompt = (
            f"Create a detailed implementation plan for: {description}. "
            "Output as structured markdown with phases, tasks, estimated effort, "
            "dependencies, and risks."
        )
        return await self._run_claude(
            prompt, working_directory=wd, timeout=timeout,
            allowed_tools=user_tools or ["Read", "Grep", "Glob"],
        )

    # ---- review_code ----

    async def _action_review_code(
        self, params: dict, *, timeout: int, user_tools: list[str] | None,
    ) -> dict[str, Any]:
        file_path = params.get("file_path")
        if not file_path:
            return {"success": False, "error": "Missing required parameter: file_path"}
        if err := self._validate_file_path(file_path):
            return {"success": False, "error": err}

        review_type = params.get("review_type", "all")
        wd = params.get("working_directory") or str(Path(file_path).parent)

        focus = {
            "security": "security vulnerabilities, injection risks, auth issues, and data exposure",
            "performance": "performance bottlenecks, memory leaks, N+1 queries, and algorithmic complexity",
            "quality": "code quality, readability, SOLID principles, error handling, and maintainability",
            "all": "security vulnerabilities, performance issues, code quality, and best practices",
        }.get(review_type, "all aspects")

        prompt = (
            f"Review the code at '{file_path}' focusing on {focus}. "
            "For each issue found, provide: severity (critical/high/medium/low), "
            "location (file:line), description, and a suggested fix. "
            "End with a summary score out of 10."
        )
        return await self._run_claude(
            prompt, working_directory=wd, timeout=timeout,
            allowed_tools=user_tools or ALLOWED_TOOLS.get("review_code"),
        )

    # ---- execute_command ----

    async def _action_execute_command(
        self, params: dict, *, timeout: int, user_tools: list[str] | None,
    ) -> dict[str, Any]:
        command = params.get("command")
        if not command:
            return {"success": False, "error": "Missing required parameter: command"}

        wd = params.get("working_directory")
        if err := self._validate_working_dir(wd):
            return {"success": False, "error": err}

        prompt = (
            f"Execute the following command and report the results, including "
            f"exit code, stdout, and stderr:\n\n```\n{command}\n```"
        )
        return await self._run_claude(
            prompt, working_directory=wd, timeout=timeout,
            allowed_tools=user_tools or ["Bash"],
        )

    # ---- generate_tests ----

    async def _action_generate_tests(
        self, params: dict, *, timeout: int, user_tools: list[str] | None,
    ) -> dict[str, Any]:
        file_path = params.get("file_path")
        if not file_path:
            return {"success": False, "error": "Missing required parameter: file_path"}
        if err := self._validate_file_path(file_path):
            return {"success": False, "error": err}

        framework = params.get("test_framework", "pytest")

        prompt = (
            f"Read the source file at '{file_path}' and generate comprehensive tests "
            f"using {framework}. Include: unit tests for every public function/method, "
            "edge cases, error paths, and mocking of external dependencies. "
            "Write the test file alongside the source with proper naming conventions."
        )
        wd = params.get("working_directory") or str(Path(file_path).parent)
        return await self._run_claude(
            prompt, working_directory=wd, timeout=timeout,
            allowed_tools=user_tools or ALLOWED_TOOLS.get("generate_tests"),
        )

    # ---- refactor ----

    async def _action_refactor(
        self, params: dict, *, timeout: int, user_tools: list[str] | None,
    ) -> dict[str, Any]:
        file_path = params.get("file_path")
        if not file_path:
            return {"success": False, "error": "Missing required parameter: file_path"}
        if err := self._validate_file_path(file_path):
            return {"success": False, "error": err}

        refactor_type = params.get("refactor_type", "simplify")
        descriptions = {
            "extract_function": "Extract logical blocks into well-named functions",
            "rename": "Improve variable, function, and class names for clarity",
            "simplify": "Simplify complex logic, reduce nesting, and improve readability",
            "optimize": "Optimize for performance while maintaining readability",
            "dry": "Eliminate code duplication by extracting shared logic",
        }
        instruction = descriptions.get(refactor_type, descriptions["simplify"])

        prompt = (
            f"Refactor the code at '{file_path}'. Goal: {instruction}. "
            "Preserve all existing behavior and public API. "
            "Show the changes you made and explain why."
        )
        wd = params.get("working_directory") or str(Path(file_path).parent)
        return await self._run_claude(
            prompt, working_directory=wd, timeout=timeout,
            allowed_tools=user_tools or ["Read", "Write", "Grep", "Glob"],
        )

    # ---- fix_bug ----

    async def _action_fix_bug(
        self, params: dict, *, timeout: int, user_tools: list[str] | None,
    ) -> dict[str, Any]:
        description = params.get("description")
        if not description:
            return {"success": False, "error": "Missing required parameter: description"}

        file_path = params.get("file_path", "")
        error_message = params.get("error_message", "")

        parts = [f"Diagnose and fix this bug: {description}"]
        if file_path:
            if err := self._validate_file_path(file_path):
                return {"success": False, "error": err}
            parts.append(f"The bug is likely in: {file_path}")
        if error_message:
            parts.append(f"Error message / traceback:\n```\n{error_message}\n```")
        parts.append(
            "Steps: 1) reproduce / understand, 2) identify root cause, "
            "3) implement fix, 4) verify the fix. Explain your reasoning."
        )

        prompt = "\n\n".join(parts)
        wd = params.get("working_directory") or (
            str(Path(file_path).parent) if file_path else None
        )
        return await self._run_claude(
            prompt, working_directory=wd, timeout=timeout,
            allowed_tools=user_tools,
        )

    # ---- generate_docs ----

    async def _action_generate_docs(
        self, params: dict, *, timeout: int, user_tools: list[str] | None,
    ) -> dict[str, Any]:
        file_path = params.get("file_path")
        if not file_path:
            return {"success": False, "error": "Missing required parameter: file_path"}
        if err := self._validate_file_path(file_path):
            return {"success": False, "error": err}

        doc_type = params.get("doc_type", "api")
        type_instructions = {
            "api": (
                "Generate API documentation with endpoint descriptions, "
                "parameter schemas, response formats, and usage examples."
            ),
            "readme": (
                "Generate a comprehensive README.md with project overview, "
                "setup instructions, usage examples, and configuration."
            ),
            "inline": (
                "Add thorough inline documentation: module docstrings, "
                "function/method docstrings (with Args, Returns, Raises), "
                "and explanatory comments for complex logic."
            ),
            "architecture": (
                "Generate an architecture document describing the system design, "
                "component relationships, data flow, and key decisions."
            ),
        }
        instruction = type_instructions.get(doc_type, type_instructions["api"])

        prompt = f"For the code at '{file_path}': {instruction}"
        wd = params.get("working_directory") or str(Path(file_path).parent)
        return await self._run_claude(
            prompt, working_directory=wd, timeout=timeout,
            allowed_tools=user_tools or ALLOWED_TOOLS.get("generate_docs"),
        )

    # ---- git_workflow ----

    async def _action_git_workflow(
        self, params: dict, *, timeout: int, user_tools: list[str] | None,
    ) -> dict[str, Any]:
        operation = params.get("operation")
        if not operation:
            return {"success": False, "error": "Missing required parameter: operation"}

        wd = params.get("working_directory")
        if err := self._validate_working_dir(wd):
            return {"success": False, "error": err}

        op_prompts = {
            "commit": (
                "Review all staged and unstaged changes (git diff, git status). "
                "Create a well-structured commit: stage relevant files, write a "
                "conventional-commit message summarizing the changes."
            ),
            "branch": (
                "List branches, show current branch, and provide a summary of "
                "recent branch activity."
            ),
            "merge": (
                "Check for merge conflicts with the main branch. If conflicts exist, "
                "describe them. Otherwise describe what a merge would include."
            ),
            "diff": (
                "Show a detailed summary of all current changes (staged and unstaged), "
                "grouped by file, with a high-level description of each change."
            ),
            "log": (
                "Show recent git log (last 20 commits) with a concise summary "
                "of the project's recent activity."
            ),
            "pr_create": (
                "Analyze all changes on the current branch vs main. "
                "Draft a pull request title and description with: summary, "
                "changes list, testing notes, and any breaking changes."
            ),
            "pr_review": (
                "Review the current branch's changes for a code review. "
                "Check for bugs, style issues, missing tests, and provide "
                "actionable feedback as a reviewer would."
            ),
        }

        prompt = op_prompts.get(operation, f"Perform git operation: {operation}")
        return await self._run_claude(
            prompt, working_directory=wd, timeout=timeout,
            allowed_tools=user_tools or ["Bash", "Read", "Grep"],
        )

    # ---- dependency_audit ----

    async def _action_dependency_audit(
        self, params: dict, *, timeout: int, user_tools: list[str] | None,
    ) -> dict[str, Any]:
        wd = params.get("working_directory")
        if err := self._validate_working_dir(wd):
            return {"success": False, "error": err}

        prompt = (
            "Audit the project dependencies for security vulnerabilities and issues. "
            "Steps: "
            "1) Identify the package manager (pip/npm/yarn/cargo/go). "
            "2) Run the appropriate audit command (npm audit, pip-audit, etc.). "
            "3) Check for outdated packages. "
            "4) Report: total deps, vulnerable deps (with severity), outdated deps, "
            "and recommended actions."
        )
        return await self._run_claude(
            prompt, working_directory=wd, timeout=timeout,
            allowed_tools=user_tools or ALLOWED_TOOLS.get("dependency_audit"),
        )

    # ---- scaffold_project ----

    async def _action_scaffold_project(
        self, params: dict, *, timeout: int, user_tools: list[str] | None,
    ) -> dict[str, Any]:
        project_type = params.get("project_type")
        name = params.get("name")
        if not project_type or not name:
            return {
                "success": False,
                "error": "Missing required parameters: project_type and name",
            }

        wd = params.get("working_directory")
        if err := self._validate_working_dir(wd):
            return {"success": False, "error": err}

        features = params.get("features", [])
        features_str = ", ".join(features) if features else "standard defaults"

        type_details = {
            "react": "React with TypeScript, Vite, ESLint, Prettier",
            "fastapi": "FastAPI with Python, uvicorn, SQLAlchemy, alembic, pytest",
            "node": "Node.js with TypeScript, ESLint, Prettier, Jest",
            "python": "Python with pyproject.toml, pytest, mypy, ruff",
        }
        stack = type_details.get(project_type, project_type)

        prompt = (
            f"Scaffold a new {stack} project named '{name}' "
            f"with these features: {features_str}. "
            "Create the full directory structure, configuration files, "
            "a basic README, CI config, and a hello-world example. "
            "Use current best practices and latest stable versions."
        )
        return await self._run_claude(
            prompt, working_directory=wd, timeout=timeout,
            allowed_tools=user_tools or ["Bash", "Write", "Read"],
        )

    # ---- multi_file_edit ----

    async def _action_multi_file_edit(
        self, params: dict, *, timeout: int, user_tools: list[str] | None,
    ) -> dict[str, Any]:
        instructions = params.get("instructions")
        file_paths = params.get("file_paths")
        if not instructions:
            return {"success": False, "error": "Missing required parameter: instructions"}
        if not file_paths or not isinstance(file_paths, list):
            return {"success": False, "error": "Missing required parameter: file_paths (list)"}

        # Validate all paths
        for fp in file_paths:
            if err := self._validate_file_path(fp):
                return {"success": False, "error": err}

        wd = params.get("working_directory") or str(Path(file_paths[0]).parent)
        files_list = "\n".join(f"- {fp}" for fp in file_paths)

        prompt = (
            f"Apply the following coordinated edits across multiple files.\n\n"
            f"Files to edit:\n{files_list}\n\n"
            f"Instructions:\n{instructions}\n\n"
            "Ensure changes are consistent across all files. "
            "Show a summary of each file's changes when done."
        )
        result = await self._run_claude(
            prompt, working_directory=wd, timeout=timeout,
            allowed_tools=user_tools or ["Read", "Write", "Edit", "Grep", "Glob"],
        )
        result.setdefault("files_modified", file_paths)
        return result

"""Secret scanner tool - detect leaked secrets in files and git history."""

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any

import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

MAX_OUTPUT_BYTES = 50 * 1024
MAX_FINDINGS = 1000
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB per file

# Secret detection patterns: (name, regex, description)
SECRET_PATTERNS = [
    # AWS
    ("aws_access_key", r"(?:^|[^A-Za-z0-9/+=])(?:AKIA[0-9A-Z]{16})(?:[^A-Za-z0-9/+=]|$)", "AWS Access Key ID"),
    ("aws_secret_key", r"(?:aws_secret_access_key|secret_key)\s*[=:]\s*['\"]?([A-Za-z0-9/+=]{40})", "AWS Secret Access Key"),
    # GitHub
    ("github_pat", r"ghp_[A-Za-z0-9]{36}", "GitHub Personal Access Token"),
    ("github_oauth", r"gho_[A-Za-z0-9]{36}", "GitHub OAuth Token"),
    ("github_app", r"ghs_[A-Za-z0-9]{36}", "GitHub App Token"),
    ("github_fine_grained", r"github_pat_[A-Za-z0-9_]{22,255}", "GitHub Fine-Grained PAT"),
    # Slack
    ("slack_bot_token", r"xoxb-[0-9]{10,13}-[0-9]{10,13}-[A-Za-z0-9]{24}", "Slack Bot Token"),
    ("slack_user_token", r"xoxp-[0-9]{10,13}-[0-9]{10,13}-[0-9]{10,13}-[a-f0-9]{32}", "Slack User Token"),
    ("slack_webhook", r"https://hooks\.slack\.com/services/T[A-Z0-9]{8,}/B[A-Z0-9]{8,}/[A-Za-z0-9]{24}", "Slack Webhook URL"),
    # Private keys
    ("private_key_rsa", r"-----BEGIN RSA PRIVATE KEY-----", "RSA Private Key"),
    ("private_key_ec", r"-----BEGIN EC PRIVATE KEY-----", "EC Private Key"),
    ("private_key_openssh", r"-----BEGIN OPENSSH PRIVATE KEY-----", "OpenSSH Private Key"),
    ("private_key_generic", r"-----BEGIN PRIVATE KEY-----", "Generic Private Key"),
    # Generic passwords/secrets in config
    ("password_assignment", r"(?:password|passwd|pwd)\s*[=:]\s*['\"]([^'\"]{8,})['\"]", "Password in Config"),
    ("api_key_generic", r"(?:api_key|apikey|api-key)\s*[=:]\s*['\"]([A-Za-z0-9_\-]{16,})['\"]", "API Key in Config"),
    ("secret_generic", r"(?:secret|token)\s*[=:]\s*['\"]([A-Za-z0-9_\-]{16,})['\"]", "Secret/Token in Config"),
    # Connection strings
    ("connection_string", r"(?:postgresql|mysql|mongodb|redis|amqp)://[^\s'\"]+:[^\s'\"]+@[^\s'\"]+", "Database Connection String"),
    # Bearer tokens in code
    ("bearer_token", r"['\"]Bearer\s+[A-Za-z0-9\-._~+/]+=*['\"]", "Hardcoded Bearer Token"),
    # Azure
    ("azure_storage_key", r"DefaultEndpointsProtocol=https;AccountName=[^;]+;AccountKey=[A-Za-z0-9+/=]{88}", "Azure Storage Key"),
    # Google
    ("gcp_api_key", r"AIza[0-9A-Za-z\-_]{35}", "Google API Key"),
    ("gcp_service_account", r'"type"\s*:\s*"service_account"', "GCP Service Account JSON"),
    # Stripe
    ("stripe_secret", r"sk_live_[0-9a-zA-Z]{24,}", "Stripe Secret Key"),
    ("stripe_restricted", r"rk_live_[0-9a-zA-Z]{24,}", "Stripe Restricted Key"),
    # SendGrid
    ("sendgrid_key", r"SG\.[A-Za-z0-9\-_]{22}\.[A-Za-z0-9\-_]{43}", "SendGrid API Key"),
    # Twilio
    ("twilio_key", r"SK[0-9a-fA-F]{32}", "Twilio API Key"),
]

# File extensions to skip
SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
    ".mp3", ".mp4", ".avi", ".mov", ".wav",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".exe", ".dll", ".so", ".dylib",
    ".pyc", ".pyo", ".class", ".o",
    ".woff", ".woff2", ".ttf", ".eot",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
}

# Directories to skip
SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
    ".eggs", "*.egg-info", ".cache",
}


def _mask_value(value: str) -> str:
    """Mask a secret value, showing only first and last few chars."""
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "*" * (len(value) - 8) + value[-4:]


class SecretScannerTool(BaseTool):
    name = "secret_scanner"
    description = (
        "Scan files, directories, and git history for leaked secrets. "
        "Detects AWS keys, GitHub tokens, Slack tokens, private keys, "
        "passwords in configs, connection strings, and more. "
        "Returns masked values for safety. Max 1000 findings."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["scan_file", "scan_directory", "scan_git_history"],
                "description": "Scanning action to perform.",
            },
            "file_path": {
                "type": "string",
                "description": "File path to scan (for scan_file).",
            },
            "dir_path": {
                "type": "string",
                "description": "Directory path to scan (for scan_directory).",
            },
            "recursive": {
                "type": "boolean",
                "description": "Scan recursively (for scan_directory). Default: true.",
            },
            "repo_path": {
                "type": "string",
                "description": "Git repo path (for scan_git_history).",
            },
            "max_commits": {
                "type": "integer",
                "description": "Max commits to scan (for scan_git_history). Default: 50.",
            },
        },
        "required": ["action"],
    }

    def _scan_content(self, content: str, file_path: str) -> list[dict]:
        """Scan text content for secrets."""
        findings = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            if len(findings) >= MAX_FINDINGS:
                break

            for pattern_name, pattern, description in SECRET_PATTERNS:
                try:
                    for match in re.finditer(pattern, line, re.IGNORECASE):
                        matched_text = match.group(0)
                        findings.append({
                            "file": file_path,
                            "line": line_num,
                            "type": pattern_name,
                            "description": description,
                            "masked_value": _mask_value(matched_text.strip()),
                            "context": line.strip()[:200],
                        })
                        if len(findings) >= MAX_FINDINGS:
                            break
                except re.error:
                    continue

        return findings

    def _should_skip_file(self, path: Path) -> bool:
        """Check if a file should be skipped."""
        if path.suffix.lower() in SKIP_EXTENSIONS:
            return True
        if path.stat().st_size > MAX_FILE_SIZE:
            return True
        return False

    def _should_skip_dir(self, dir_name: str) -> bool:
        """Check if a directory should be skipped."""
        return dir_name in SKIP_DIRS

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action")
        logger.info("secret_scanner_execute", action=action)

        try:
            if action == "scan_file":
                return await self._scan_file(kwargs)
            elif action == "scan_directory":
                return await self._scan_directory(kwargs)
            elif action == "scan_git_history":
                return await self._scan_git_history(kwargs)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except Exception as e:
            logger.error("secret_scanner_error", error=str(e))
            return json.dumps({"error": f"Secret scanning failed: {e}"})

    async def _scan_file(self, kwargs: dict) -> str:
        file_path = kwargs.get("file_path", "")
        if not file_path:
            return json.dumps({"error": "file_path is required"})

        path = Path(file_path)
        if not path.exists():
            return json.dumps({"error": f"File not found: {file_path}"})
        if not path.is_file():
            return json.dumps({"error": f"Not a file: {file_path}"})
        if self._should_skip_file(path):
            return json.dumps({"findings": [], "skipped": True, "reason": "Binary or oversized file"})

        try:
            content = path.read_text(errors="replace")
        except Exception as e:
            return json.dumps({"error": f"Cannot read file: {e}"})

        findings = self._scan_content(content, file_path)

        # Group by type
        type_counts: dict[str, int] = {}
        for f in findings:
            type_counts[f["type"]] = type_counts.get(f["type"], 0) + 1

        logger.info("secret_scan_file_done", file=file_path, findings=len(findings))
        return json.dumps({
            "file": file_path,
            "findings": findings,
            "finding_count": len(findings),
            "types_found": type_counts,
        })

    async def _scan_directory(self, kwargs: dict) -> str:
        dir_path = kwargs.get("dir_path", "")
        recursive = kwargs.get("recursive", True)

        if not dir_path:
            return json.dumps({"error": "dir_path is required"})

        root = Path(dir_path)
        if not root.is_dir():
            return json.dumps({"error": f"Directory not found: {dir_path}"})

        all_findings: list[dict] = []
        files_scanned = 0
        files_skipped = 0

        if recursive:
            walk_iter = root.rglob("*")
        else:
            walk_iter = root.glob("*")

        for path in walk_iter:
            if len(all_findings) >= MAX_FINDINGS:
                break

            # Skip directories
            if path.is_dir():
                continue

            # Skip hidden/excluded dirs
            parts = path.relative_to(root).parts
            if any(self._should_skip_dir(p) for p in parts):
                files_skipped += 1
                continue

            if self._should_skip_file(path):
                files_skipped += 1
                continue

            try:
                content = path.read_text(errors="replace")
                findings = self._scan_content(content, str(path))
                all_findings.extend(findings)
                files_scanned += 1
            except Exception:
                files_skipped += 1
                continue

        # Group by type
        type_counts: dict[str, int] = {}
        for f in all_findings:
            type_counts[f["type"]] = type_counts.get(f["type"], 0) + 1

        # Group by file
        files_with_findings: dict[str, int] = {}
        for f in all_findings:
            files_with_findings[f["file"]] = files_with_findings.get(f["file"], 0) + 1

        logger.info(
            "secret_scan_dir_done",
            dir=dir_path,
            findings=len(all_findings),
            files_scanned=files_scanned,
        )

        result = {
            "directory": dir_path,
            "findings": all_findings[:MAX_FINDINGS],
            "finding_count": len(all_findings),
            "files_scanned": files_scanned,
            "files_skipped": files_skipped,
            "types_found": type_counts,
            "files_with_findings": files_with_findings,
            "truncated": len(all_findings) > MAX_FINDINGS,
        }
        output = json.dumps(result)
        if len(output) > MAX_OUTPUT_BYTES:
            return output[:MAX_OUTPUT_BYTES] + "\n... [output truncated]"
        return output

    async def _scan_git_history(self, kwargs: dict) -> str:
        repo_path = kwargs.get("repo_path", "")
        max_commits = kwargs.get("max_commits", 50)

        if not repo_path:
            return json.dumps({"error": "repo_path is required"})
        if not Path(repo_path).is_dir():
            return json.dumps({"error": f"Repository not found: {repo_path}"})

        try:
            # Get commit list
            proc = await asyncio.create_subprocess_exec(
                "git", "log", f"--max-count={max_commits}", "--format=%H",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=repo_path,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

            if proc.returncode != 0:
                return json.dumps({"error": f"git log failed: {stderr.decode()}"})

            commits = stdout.decode().strip().split("\n")
            commits = [c.strip() for c in commits if c.strip()]

        except asyncio.TimeoutError:
            return json.dumps({"error": "git log timed out"})
        except FileNotFoundError:
            return json.dumps({"error": "git executable not found"})

        all_findings: list[dict] = []
        commits_scanned = 0

        for commit_sha in commits:
            if len(all_findings) >= MAX_FINDINGS:
                break

            try:
                # Get diff for commit
                proc = await asyncio.create_subprocess_exec(
                    "git", "show", "--format=", "--diff-filter=AM", "-p", commit_sha,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=repo_path,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

                if proc.returncode != 0:
                    continue

                diff_content = stdout.decode(errors="replace")

                # Only scan added lines
                added_lines = []
                current_file = ""
                for line in diff_content.split("\n"):
                    if line.startswith("diff --git"):
                        # Extract filename
                        parts = line.split(" b/")
                        current_file = parts[-1] if len(parts) > 1 else ""
                    elif line.startswith("+") and not line.startswith("+++"):
                        added_lines.append((current_file, line[1:]))

                # Scan added lines
                for file_name, added_line in added_lines:
                    if len(all_findings) >= MAX_FINDINGS:
                        break
                    for pattern_name, pattern, description in SECRET_PATTERNS:
                        try:
                            if re.search(pattern, added_line, re.IGNORECASE):
                                match = re.search(pattern, added_line, re.IGNORECASE)
                                if match:
                                    all_findings.append({
                                        "commit": commit_sha[:8],
                                        "file": file_name,
                                        "type": pattern_name,
                                        "description": description,
                                        "masked_value": _mask_value(match.group(0).strip()),
                                    })
                        except re.error:
                            continue

                commits_scanned += 1
            except asyncio.TimeoutError:
                continue
            except Exception:
                continue

        # Group by type
        type_counts: dict[str, int] = {}
        for f in all_findings:
            type_counts[f["type"]] = type_counts.get(f["type"], 0) + 1

        logger.info(
            "secret_scan_git_done",
            repo=repo_path,
            commits=commits_scanned,
            findings=len(all_findings),
        )

        result = {
            "repository": repo_path,
            "commits_scanned": commits_scanned,
            "commits_total": len(commits),
            "findings": all_findings[:MAX_FINDINGS],
            "finding_count": len(all_findings),
            "types_found": type_counts,
            "truncated": len(all_findings) > MAX_FINDINGS,
        }
        output = json.dumps(result)
        if len(output) > MAX_OUTPUT_BYTES:
            return output[:MAX_OUTPUT_BYTES] + "\n... [output truncated]"
        return output

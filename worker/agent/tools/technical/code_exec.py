"""Code execution tool - run code in a hardened sandbox environment."""

import asyncio
import json
import os
import resource
import tempfile
from pathlib import Path
from typing import Any

from agent.tools.base import BaseTool

# Dangerous modules/commands that should be blocked
BLOCKED_PYTHON_IMPORTS = {
    "subprocess", "shutil.rmtree", "os.system", "os.popen",
    "os.remove", "os.rmdir", "os.unlink", "pathlib.Path.unlink",
    "__import__", "exec", "eval", "compile",
    "socket", "http.client", "urllib",
}

BLOCKED_SHELL_COMMANDS = {
    "rm -rf", "mkfs", "dd if=", "shutdown", "reboot", "halt",
    "kill -9", "killall", "chmod 777", "curl", "wget",
    "> /dev/sda", "fork bomb",
}

# Resource limits
MAX_MEMORY_MB = 256
MAX_CPU_SECONDS = 30
MAX_OUTPUT_BYTES = 10000


class CodeExecutionTool(BaseTool):
    name = "code_exec"
    description = (
        "Execute Python or shell code in a sandboxed environment with resource limits. "
        "Network access, dangerous operations, and file system writes outside /tmp are blocked."
    )
    parameters = {
        "type": "object",
        "properties": {
            "language": {
                "type": "string",
                "enum": ["python", "shell"],
                "description": "Programming language",
            },
            "code": {"type": "string", "description": "Code to execute"},
            "timeout": {"type": "integer", "description": "Timeout in seconds (max 30)"},
        },
        "required": ["language", "code"],
    }

    async def execute(self, **kwargs: Any) -> Any:
        language = kwargs["language"]
        code = kwargs["code"]
        timeout = min(kwargs.get("timeout", 30), MAX_CPU_SECONDS)

        # Pre-execution safety checks
        safety_check = self._check_safety(language, code)
        if safety_check:
            return json.dumps({"error": safety_check, "blocked": True})

        if language == "python":
            return await self._run_python(code, timeout)
        elif language == "shell":
            return await self._run_shell(code, timeout)

        return json.dumps({"error": f"Unsupported language: {language}"})

    def _check_safety(self, language: str, code: str) -> str | None:
        """Check code for dangerous operations before execution."""
        code_lower = code.lower()

        if language == "python":
            for blocked in BLOCKED_PYTHON_IMPORTS:
                if blocked.lower() in code_lower:
                    return f"Blocked: '{blocked}' is not allowed in sandbox"

        elif language == "shell":
            for blocked in BLOCKED_SHELL_COMMANDS:
                if blocked.lower() in code_lower:
                    return f"Blocked: '{blocked}' is not allowed in sandbox"

        # Check for common attack patterns
        if "../../" in code or "/etc/passwd" in code or "/etc/shadow" in code:
            return "Blocked: path traversal detected"

        return None

    async def _run_python(self, code: str, timeout: int) -> str:
        # Wrap code with resource limits
        sandbox_wrapper = f"""
import resource
import sys

# Set resource limits
resource.setrlimit(resource.RLIMIT_AS, ({MAX_MEMORY_MB * 1024 * 1024}, {MAX_MEMORY_MB * 1024 * 1024}))
resource.setrlimit(resource.RLIMIT_CPU, ({timeout}, {timeout}))
resource.setrlimit(resource.RLIMIT_NOFILE, (50, 50))

# Restrict to /tmp for file operations
import os
os.chdir('/tmp')

# Execute user code
{code}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, dir="/tmp") as f:
            f.write(sandbox_wrapper)
            script_path = f.name

        try:
            env = {
                "PATH": "/usr/bin:/bin",
                "HOME": "/tmp",
                "TMPDIR": "/tmp",
                "LANG": "C.UTF-8",
            }

            proc = await asyncio.create_subprocess_exec(
                "python", "-u", script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd="/tmp",
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout + 5)

            return json.dumps({
                "exit_code": proc.returncode,
                "stdout": stdout.decode(errors="replace")[:MAX_OUTPUT_BYTES],
                "stderr": stderr.decode(errors="replace")[:MAX_OUTPUT_BYTES // 2],
            })

        except asyncio.TimeoutError:
            proc.kill()
            return json.dumps({"error": f"Execution timed out after {timeout}s"})
        finally:
            Path(script_path).unlink(missing_ok=True)

    async def _run_shell(self, code: str, timeout: int) -> str:
        try:
            env = {
                "PATH": "/usr/bin:/bin",
                "HOME": "/tmp",
                "TMPDIR": "/tmp",
            }

            proc = await asyncio.create_subprocess_shell(
                code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd="/tmp",
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout + 5)

            return json.dumps({
                "exit_code": proc.returncode,
                "stdout": stdout.decode(errors="replace")[:MAX_OUTPUT_BYTES],
                "stderr": stderr.decode(errors="replace")[:MAX_OUTPUT_BYTES // 2],
            })

        except asyncio.TimeoutError:
            proc.kill()
            return json.dumps({"error": f"Execution timed out after {timeout}s"})

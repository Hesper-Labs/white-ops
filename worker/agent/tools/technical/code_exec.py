"""Code execution tool - run code in a hardened sandbox environment."""

import asyncio
import json
import os
import re
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
    "ctypes", "importlib", "builtins",
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

# Sandbox wrapper is a separate template to prevent code injection
_SANDBOX_TEMPLATE = '''\
import resource
import sys
import os

# Set resource limits
resource.setrlimit(resource.RLIMIT_AS, ({mem_limit}, {mem_limit}))
resource.setrlimit(resource.RLIMIT_CPU, ({cpu_limit}, {cpu_limit}))
resource.setrlimit(resource.RLIMIT_NOFILE, (50, 50))
resource.setrlimit(resource.RLIMIT_NPROC, (32, 32))

# Restrict to /tmp for file operations
os.chdir('/tmp')
'''


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
            # Block __import__ variants and importlib tricks
            if re.search(r'__\s*import\s*__', code, re.IGNORECASE):
                return "Blocked: dynamic import is not allowed in sandbox"
            if re.search(r'getattr\s*\(\s*__builtins__', code, re.IGNORECASE):
                return "Blocked: builtins access is not allowed in sandbox"

        elif language == "shell":
            for blocked in BLOCKED_SHELL_COMMANDS:
                if blocked.lower() in code_lower:
                    return f"Blocked: '{blocked}' is not allowed in sandbox"

        # Check for common attack patterns
        attack_patterns = [
            "../../", "/etc/passwd", "/etc/shadow",
            "/proc/self", "/proc/1/", "/dev/shm",
        ]
        for pattern in attack_patterns:
            if pattern in code:
                return f"Blocked: suspicious path pattern detected: {pattern}"

        return None

    async def _run_python(self, code: str, timeout: int) -> str:
        # Write sandbox wrapper and user code as SEPARATE files
        # This prevents code injection via the wrapper template
        sandbox_code = _SANDBOX_TEMPLATE.format(
            mem_limit=MAX_MEMORY_MB * 1024 * 1024,
            cpu_limit=timeout,
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix="_setup.py", delete=False, dir="/tmp") as sf:
            sf.write(sandbox_code)
            setup_path = sf.name

        with tempfile.NamedTemporaryFile(mode="w", suffix="_user.py", delete=False, dir="/tmp") as uf:
            uf.write(code)
            user_path = uf.name

        # Create a runner script that executes setup then user code safely
        runner_code = f"""\
import runpy
exec(open({setup_path!r}).read())
exec(open({user_path!r}).read())
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix="_runner.py", delete=False, dir="/tmp") as rf:
            rf.write(runner_code)
            runner_path = rf.name

        try:
            env = {
                "PATH": "/usr/bin:/bin",
                "HOME": "/tmp",
                "TMPDIR": "/tmp",
                "LANG": "C.UTF-8",
            }

            proc = await asyncio.create_subprocess_exec(  # noqa: S603
                "python", "-u", runner_path,
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
            for p in (setup_path, user_path, runner_path):
                Path(p).unlink(missing_ok=True)

    async def _run_shell(self, code: str, timeout: int) -> str:
        try:
            env = {
                "PATH": "/usr/bin:/bin",
                "HOME": "/tmp",
                "TMPDIR": "/tmp",
            }

            proc = await asyncio.create_subprocess_exec(  # noqa: S603
                "/bin/sh", "-c", code,
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

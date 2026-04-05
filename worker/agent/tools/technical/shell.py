"""Shell command execution tool with safety restrictions."""

import asyncio
import json
import shlex
from typing import Any

from agent.tools.base import BaseTool


class ShellTool(BaseTool):
    name = "shell"
    description = (
        "Execute shell commands with safety restrictions. "
        "Dangerous commands like rm -rf, mkfs, and shutdown are blocked."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["execute"],
                "description": "Shell action to perform",
            },
            "command": {
                "type": "string",
                "description": "Shell command to execute",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (default 30, max 120)",
            },
            "cwd": {
                "type": "string",
                "description": "Working directory for the command",
            },
        },
        "required": ["action", "command"],
    }

    # Dangerous commands and patterns that should be blocked
    BLOCKED_COMMANDS = [
        "rm -rf /",
        "rm -rf /*",
        "rm -rf ~",
        "rm -rf .",
        "mkfs",
        "dd if=",
        "shutdown",
        "reboot",
        "halt",
        "poweroff",
        "init 0",
        "init 6",
        ":(){ :|:& };:",  # fork bomb
        "> /dev/sda",
        "chmod -R 777 /",
        "chown -R",
        "mv /* ",
        "wget|sh",
        "curl|sh",
        "wget|bash",
        "curl|bash",
        "> /etc/passwd",
        "> /etc/shadow",
        "format c:",
        "del /f /s /q",
    ]

    BLOCKED_EXECUTABLES = [
        "mkfs",
        "fdisk",
        "parted",
        "shutdown",
        "reboot",
        "halt",
        "poweroff",
        "systemctl poweroff",
        "systemctl reboot",
    ]

    def _is_dangerous(self, command: str) -> str | None:
        """Check if a command is dangerous. Returns reason if blocked, None if safe."""
        cmd_lower = command.lower().strip()

        # Check blocked patterns
        for pattern in self.BLOCKED_COMMANDS:
            if pattern.lower() in cmd_lower:
                return f"Blocked dangerous pattern: {pattern}"

        # Check blocked executables
        try:
            parts = shlex.split(cmd_lower)
            if parts:
                base_cmd = parts[0].split("/")[-1]  # handle /usr/bin/xxx paths
                if base_cmd in self.BLOCKED_EXECUTABLES:
                    return f"Blocked dangerous command: {base_cmd}"
        except ValueError:
            pass  # Malformed command, let the shell handle the error

        # Check for recursive rm with force on broad paths
        if "rm " in cmd_lower and ("-rf" in cmd_lower or "-fr" in cmd_lower):
            try:
                parts = shlex.split(command)
                for part in parts:
                    if part in ("/", "/*", "~", ".", ".."):
                        return f"Blocked dangerous rm target: {part}"
            except ValueError:
                pass

        return None

    async def execute(self, **kwargs: Any) -> Any:
        if kwargs.get("action") != "execute":
            return json.dumps({"error": "Only 'execute' action is supported"})

        command = kwargs.get("command", "")
        if not command:
            return json.dumps({"error": "command is required"})

        # Safety check
        danger = self._is_dangerous(command)
        if danger:
            return json.dumps({
                "error": f"Command blocked for safety: {danger}",
                "command": command,
                "blocked": True,
            })

        timeout = min(kwargs.get("timeout", 30), 120)
        cwd = kwargs.get("cwd")

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )

            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            # Truncate large outputs
            max_output = 10000
            stdout_truncated = len(stdout_str) > max_output
            stderr_truncated = len(stderr_str) > max_output

            return json.dumps({
                "exit_code": proc.returncode,
                "stdout": stdout_str[:max_output],
                "stderr": stderr_str[:max_output],
                "stdout_truncated": stdout_truncated,
                "stderr_truncated": stderr_truncated,
            })
        except asyncio.TimeoutError:
            return json.dumps({
                "error": f"Command timed out after {timeout} seconds",
                "command": command,
            })
        except FileNotFoundError:
            return json.dumps({"error": "Shell not available"})
        except OSError as e:
            return json.dumps({"error": f"OS error: {e}"})

"""Docker operations tool - manage containers, view logs and stats."""

import asyncio
import json
from typing import Any

from agent.tools.base import BaseTool


class DockerOpsTool(BaseTool):
    name = "docker_ops"
    description = (
        "Manage Docker containers. List running containers, view logs, "
        "check resource usage stats, and restart containers."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list_containers", "logs", "stats", "restart"],
                "description": "The Docker action to perform",
            },
            "container": {
                "type": "string",
                "description": "Container name or ID (required for logs, stats, restart)",
            },
            "tail": {
                "type": "integer",
                "description": "Number of log lines to show (default 50)",
            },
            "all": {
                "type": "boolean",
                "description": "Show all containers including stopped (default false)",
            },
            "since": {
                "type": "string",
                "description": "Show logs since timestamp or relative (e.g., '1h', '2024-01-01')",
            },
        },
        "required": ["action"],
    }

    async def _run_docker(self, args: list[str]) -> tuple[int, str, str]:
        """Run a docker command and return (returncode, stdout, stderr)."""
        proc = await asyncio.create_subprocess_exec(
            "docker", *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        return (
            proc.returncode or 0,
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
        )

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]

        try:
            if action == "list_containers":
                return await self._list_containers(kwargs)
            elif action == "logs":
                return await self._logs(kwargs)
            elif action == "stats":
                return await self._stats(kwargs)
            elif action == "restart":
                return await self._restart(kwargs)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except asyncio.TimeoutError:
            return json.dumps({"error": "Docker command timed out after 30 seconds"})
        except FileNotFoundError:
            return json.dumps({"error": "docker executable not found"})

    async def _list_containers(self, kwargs: dict) -> str:
        args = [
            "ps",
            "--format", "{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}|{{.State}}",
        ]
        if kwargs.get("all"):
            args.insert(1, "-a")

        code, stdout, stderr = await self._run_docker(args)
        if code != 0:
            return json.dumps({"error": stderr.strip()})

        containers = []
        for line in stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("|", 5)
                if len(parts) >= 6:
                    containers.append({
                        "id": parts[0][:12],
                        "name": parts[1],
                        "image": parts[2],
                        "status": parts[3],
                        "ports": parts[4],
                        "state": parts[5],
                    })
        return json.dumps({"containers": containers, "count": len(containers)})

    async def _logs(self, kwargs: dict) -> str:
        container = kwargs.get("container")
        if not container:
            return json.dumps({"error": "container is required"})

        tail = kwargs.get("tail", 50)
        args = ["logs", "--tail", str(tail)]

        if kwargs.get("since"):
            args.extend(["--since", kwargs["since"]])

        args.append(container)

        code, stdout, stderr = await self._run_docker(args)
        if code != 0:
            return json.dumps({"error": stderr.strip()})

        # Docker often outputs to stderr for logs
        output = stdout or stderr
        return json.dumps({
            "container": container,
            "lines": output.strip().split("\n") if output.strip() else [],
            "line_count": len(output.strip().split("\n")) if output.strip() else 0,
        })

    async def _stats(self, kwargs: dict) -> str:
        container = kwargs.get("container")
        if not container:
            return json.dumps({"error": "container is required"})

        code, stdout, stderr = await self._run_docker(
            ["stats", "--no-stream", "--format",
             "{{.Container}}|{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}|{{.MemPerc}}|{{.NetIO}}|{{.BlockIO}}|{{.PIDs}}",
             container]
        )
        if code != 0:
            return json.dumps({"error": stderr.strip()})

        line = stdout.strip()
        if not line:
            return json.dumps({"error": "No stats available"})

        parts = line.split("|", 7)
        if len(parts) >= 8:
            return json.dumps({
                "container_id": parts[0],
                "name": parts[1],
                "cpu_percent": parts[2],
                "memory_usage": parts[3],
                "memory_percent": parts[4],
                "net_io": parts[5],
                "block_io": parts[6],
                "pids": parts[7],
            })
        return json.dumps({"raw": line})

    async def _restart(self, kwargs: dict) -> str:
        container = kwargs.get("container")
        if not container:
            return json.dumps({"error": "container is required"})

        code, stdout, stderr = await self._run_docker(["restart", container])
        if code == 0:
            return json.dumps({"success": True, "container": container, "output": stdout.strip()})
        return json.dumps({"error": stderr.strip()})

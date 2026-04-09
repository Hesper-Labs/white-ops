"""Docker operations tool - manage containers, images, and compose stacks."""

import asyncio
import json
import re
from typing import Any

import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

MAX_OUTPUT_BYTES = 50 * 1024
COMMAND_TIMEOUT = 60  # seconds

# Blocked flags for security
BLOCKED_FLAGS = {"--privileged", "--network=host", "--net=host", "--pid=host", "--cap-add=ALL"}


def _truncate(text: str) -> str:
    if len(text) > MAX_OUTPUT_BYTES:
        return text[:MAX_OUTPUT_BYTES] + "\n... [output truncated]"
    return text


class DockerOpsTool(BaseTool):
    name = "docker_ops"
    description = (
        "Manage Docker containers, images, and compose stacks. "
        "List, start, stop, inspect containers; view logs; list and build images; "
        "run compose up/down. Blocks --privileged and --network host for safety."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "list_containers", "container_logs", "start_container",
                    "stop_container", "inspect_container", "list_images",
                    "build_image", "compose_up", "compose_down",
                ],
                "description": "Docker action to perform.",
            },
            "container_id": {
                "type": "string",
                "description": "Container name or ID.",
            },
            "all": {
                "type": "boolean",
                "description": "Include stopped containers (for list_containers). Default: false.",
            },
            "tail": {
                "type": "integer",
                "description": "Number of log lines (for container_logs). Default: 100.",
            },
            "path": {
                "type": "string",
                "description": "Dockerfile directory (for build_image) or compose file directory.",
            },
            "tag": {
                "type": "string",
                "description": "Image tag (for build_image).",
            },
        },
        "required": ["action"],
    }

    async def _run(self, args: list[str], timeout: int = COMMAND_TIMEOUT) -> tuple[int, str, str]:
        """Run a docker command safely."""
        # Check for blocked flags
        for arg in args:
            arg_lower = arg.lower()
            for blocked in BLOCKED_FLAGS:
                if arg_lower == blocked or arg_lower.startswith(blocked + "="):
                    raise PermissionError(f"Blocked flag: {blocked}")

        proc = await asyncio.create_subprocess_exec(
            "docker", *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return (
            proc.returncode or 0,
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
        )

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action")
        logger.info("docker_execute", action=action)

        try:
            if action == "list_containers":
                return await self._list_containers(kwargs)
            elif action == "container_logs":
                return await self._container_logs(kwargs)
            elif action == "start_container":
                return await self._start_container(kwargs)
            elif action == "stop_container":
                return await self._stop_container(kwargs)
            elif action == "inspect_container":
                return await self._inspect_container(kwargs)
            elif action == "list_images":
                return await self._list_images()
            elif action == "build_image":
                return await self._build_image(kwargs)
            elif action == "compose_up":
                return await self._compose_up(kwargs)
            elif action == "compose_down":
                return await self._compose_down(kwargs)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except PermissionError as e:
            return json.dumps({"error": str(e)})
        except asyncio.TimeoutError:
            logger.error("docker_timeout", action=action)
            return json.dumps({"error": f"Docker command timed out after {COMMAND_TIMEOUT}s"})
        except FileNotFoundError:
            return json.dumps({"error": "docker executable not found"})
        except Exception as e:
            logger.error("docker_error", error=str(e))
            return json.dumps({"error": f"Docker operation failed: {e}"})

    async def _list_containers(self, kwargs: dict) -> str:
        fmt = "{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}|{{.State}}|{{.CreatedAt}}"
        args = ["ps", "--format", fmt]
        if kwargs.get("all"):
            args.insert(1, "-a")

        code, stdout, stderr = await self._run(args)
        if code != 0:
            return json.dumps({"error": stderr.strip()})

        containers = []
        for line in stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("|", 6)
            if len(parts) >= 6:
                containers.append({
                    "id": parts[0][:12],
                    "name": parts[1],
                    "image": parts[2],
                    "status": parts[3],
                    "ports": parts[4],
                    "state": parts[5],
                    "created": parts[6] if len(parts) > 6 else "",
                })

        return _truncate(json.dumps({"containers": containers, "count": len(containers)}))

    async def _container_logs(self, kwargs: dict) -> str:
        container_id = kwargs.get("container_id")
        if not container_id:
            return json.dumps({"error": "container_id is required"})

        tail = kwargs.get("tail", 100)
        args = ["logs", "--tail", str(tail), container_id]

        code, stdout, stderr = await self._run(args)
        if code != 0:
            return json.dumps({"error": stderr.strip()})

        output = stdout or stderr
        return _truncate(json.dumps({
            "container": container_id,
            "lines": output.strip().split("\n") if output.strip() else [],
            "line_count": len(output.strip().split("\n")) if output.strip() else 0,
        }))

    async def _start_container(self, kwargs: dict) -> str:
        container_id = kwargs.get("container_id")
        if not container_id:
            return json.dumps({"error": "container_id is required"})

        code, stdout, stderr = await self._run(["start", container_id])
        if code == 0:
            logger.info("docker_container_started", container=container_id)
            return json.dumps({"success": True, "container": container_id})
        return json.dumps({"error": stderr.strip()})

    async def _stop_container(self, kwargs: dict) -> str:
        container_id = kwargs.get("container_id")
        if not container_id:
            return json.dumps({"error": "container_id is required"})

        code, stdout, stderr = await self._run(["stop", container_id])
        if code == 0:
            logger.info("docker_container_stopped", container=container_id)
            return json.dumps({"success": True, "container": container_id})
        return json.dumps({"error": stderr.strip()})

    async def _inspect_container(self, kwargs: dict) -> str:
        container_id = kwargs.get("container_id")
        if not container_id:
            return json.dumps({"error": "container_id is required"})

        code, stdout, stderr = await self._run(["inspect", container_id])
        if code != 0:
            return json.dumps({"error": stderr.strip()})

        try:
            data = json.loads(stdout)
            if isinstance(data, list) and data:
                info = data[0]
                result = {
                    "id": info.get("Id", "")[:12],
                    "name": info.get("Name", "").lstrip("/"),
                    "image": info.get("Config", {}).get("Image", ""),
                    "state": info.get("State", {}),
                    "created": info.get("Created", ""),
                    "network": {
                        k: {"ip": v.get("IPAddress", "")}
                        for k, v in info.get("NetworkSettings", {}).get("Networks", {}).items()
                    },
                    "mounts": [
                        {"source": m.get("Source"), "destination": m.get("Destination"), "mode": m.get("Mode")}
                        for m in info.get("Mounts", [])
                    ],
                    "env_count": len(info.get("Config", {}).get("Env", [])),
                    "ports": info.get("NetworkSettings", {}).get("Ports", {}),
                }
                return _truncate(json.dumps(result))
            return _truncate(stdout)
        except json.JSONDecodeError:
            return _truncate(stdout)

    async def _list_images(self) -> str:
        fmt = "{{.Repository}}|{{.Tag}}|{{.ID}}|{{.Size}}|{{.CreatedAt}}"
        code, stdout, stderr = await self._run(["images", "--format", fmt])
        if code != 0:
            return json.dumps({"error": stderr.strip()})

        images = []
        for line in stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("|", 4)
            if len(parts) >= 4:
                images.append({
                    "repository": parts[0],
                    "tag": parts[1],
                    "id": parts[2][:12],
                    "size": parts[3],
                    "created": parts[4] if len(parts) > 4 else "",
                })

        return _truncate(json.dumps({"images": images, "count": len(images)}))

    async def _build_image(self, kwargs: dict) -> str:
        path = kwargs.get("path", ".")
        tag = kwargs.get("tag")

        args = ["build"]
        if tag:
            # Validate tag format
            if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9._\-/]*:[a-zA-Z0-9._\-]*$", tag):
                if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9._\-/]*$", tag):
                    return json.dumps({"error": "Invalid image tag format"})
            args.extend(["-t", tag])
        args.append(path)

        code, stdout, stderr = await self._run(args, timeout=300)
        if code == 0:
            logger.info("docker_image_built", tag=tag, path=path)
            return _truncate(json.dumps({"success": True, "tag": tag, "output": stdout[-2000:]}))
        return _truncate(json.dumps({"error": stderr[-2000:]}))

    async def _compose_up(self, kwargs: dict) -> str:
        path = kwargs.get("path", ".")
        args = ["compose", "-f", f"{path}/docker-compose.yml", "up", "-d"]

        code, stdout, stderr = await self._run(args, timeout=120)
        output = stdout + stderr
        if code == 0:
            logger.info("docker_compose_up", path=path)
            return _truncate(json.dumps({"success": True, "output": output[-2000:]}))
        return _truncate(json.dumps({"error": output[-2000:]}))

    async def _compose_down(self, kwargs: dict) -> str:
        path = kwargs.get("path", ".")
        args = ["compose", "-f", f"{path}/docker-compose.yml", "down"]

        code, stdout, stderr = await self._run(args, timeout=60)
        output = stdout + stderr
        if code == 0:
            logger.info("docker_compose_down", path=path)
            return _truncate(json.dumps({"success": True, "output": output[-2000:]}))
        return _truncate(json.dumps({"error": output[-2000:]}))

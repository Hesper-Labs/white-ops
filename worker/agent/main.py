"""White-Ops Agent Worker - Main entry point.

Connects to the master server, registers as a worker,
sends heartbeats, and processes assigned tasks.
"""

import asyncio
import platform
import signal

import httpx
import psutil
import structlog

from agent.config import settings
from agent.executor import TaskExecutor

logger = structlog.get_logger()


class Worker:
    def __init__(self) -> None:
        self.client = httpx.AsyncClient(base_url=settings.master_url, timeout=30)
        self.executor = TaskExecutor()
        self.running = True
        self.worker_id: str | None = None

    async def register(self) -> None:
        """Register this worker with the master server."""
        system_info = {
            "os": platform.system(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
        }

        payload = {
            "name": settings.worker_name,
            "hostname": platform.node(),
            "ip_address": self._get_ip(),
            "max_agents": settings.worker_max_agents,
            "cpu_cores": psutil.cpu_count(),
            "memory_total_mb": psutil.virtual_memory().total // (1024 * 1024),
            "os_info": system_info,
        }

        try:
            response = await self.client.post("/api/v1/workers/register", json=payload)
            if response.status_code == 200:
                data = response.json()
                self.worker_id = data["id"]
                logger.info("worker_registered", worker_id=self.worker_id, name=settings.worker_name)
            else:
                logger.error("registration_failed", status=response.status_code, body=response.text)
        except httpx.ConnectError:
            logger.warning("master_unreachable", url=settings.master_url)

    async def heartbeat(self) -> None:
        """Send periodic heartbeat with system metrics."""
        while self.running:
            if self.worker_id:
                try:
                    payload = {
                        "cpu_usage_percent": psutil.cpu_percent(interval=1),
                        "memory_usage_percent": psutil.virtual_memory().percent,
                        "disk_usage_percent": psutil.disk_usage("/").percent,
                    }
                    await self.client.post(
                        f"/api/v1/workers/{self.worker_id}/heartbeat", json=payload
                    )
                except Exception as e:
                    logger.warning("heartbeat_failed", error=str(e))

            await asyncio.sleep(settings.heartbeat_interval)

    async def poll_tasks(self) -> None:
        """Poll for assigned tasks and execute them."""
        while self.running:
            if self.worker_id:
                try:
                    response = await self.client.get(
                        f"/api/v1/workers/{self.worker_id}/tasks"
                    )
                    if response.status_code == 200:
                        tasks = response.json()
                        for task in tasks:
                            logger.info("task_received", task_id=task["id"], title=task["title"])
                            asyncio.create_task(self.executor.execute(task, self.client))
                except Exception as e:
                    logger.warning("poll_failed", error=str(e))

            await asyncio.sleep(5)

    def _get_ip(self) -> str:
        """Get the worker's IP address."""
        import socket

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    async def run(self) -> None:
        logger.info("worker_starting", name=settings.worker_name, master=settings.master_url)

        await self.register()

        tasks = [
            asyncio.create_task(self.heartbeat()),
            asyncio.create_task(self.poll_tasks()),
        ]

        def handle_shutdown(*_: object) -> None:
            self.running = False
            for t in tasks:
                t.cancel()

        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            pass
        finally:
            await self.client.aclose()
            logger.info("worker_stopped")


async def main() -> None:
    worker = Worker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())

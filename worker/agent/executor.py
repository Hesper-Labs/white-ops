"""Task executor - runs tasks using LLM and tools."""

import traceback
from datetime import datetime, timezone

import httpx
import structlog

from agent.llm.provider import LLMProvider
from agent.tools.registry import ToolRegistry

logger = structlog.get_logger()


class TaskExecutor:
    def __init__(self) -> None:
        self.llm = LLMProvider()
        self.tools = ToolRegistry()

    async def execute(self, task: dict, client: httpx.AsyncClient) -> None:
        """Execute a task assigned by the master server."""
        task_id = task["id"]

        try:
            # Update status to in_progress
            await client.patch(
                f"/api/v1/tasks/{task_id}",
                json={"status": "in_progress"},
            )

            logger.info("task_started", task_id=task_id, title=task.get("title"))

            # Build the prompt for the LLM
            system_prompt = self._build_system_prompt(task)
            user_prompt = self._build_user_prompt(task)

            # Get available tools for this task
            available_tools = self.tools.get_tool_definitions(
                task.get("required_tools", [])
            )

            # Run the LLM agent loop
            result = await self._agent_loop(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                tools=available_tools,
                task_id=task_id,
            )

            # Report success
            await client.patch(
                f"/api/v1/tasks/{task_id}",
                json={
                    "status": "completed",
                    "result": result,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            logger.info("task_completed", task_id=task_id)

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            logger.error("task_failed", task_id=task_id, error=str(e))

            await client.patch(
                f"/api/v1/tasks/{task_id}",
                json={
                    "status": "failed",
                    "error": error_msg,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                },
            )

    async def _agent_loop(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict],
        task_id: str,
        max_iterations: int = 20,
    ) -> str:
        """Run the LLM agent loop with tool calling."""
        messages = [{"role": "user", "content": user_prompt}]

        for iteration in range(max_iterations):
            response = await self.llm.chat(
                system=system_prompt,
                messages=messages,
                tools=tools if tools else None,
            )

            # Check if the LLM wants to call tools
            if response.get("tool_calls"):
                messages.append({"role": "assistant", "content": response.get("content", ""), "tool_calls": response["tool_calls"]})

                for tool_call in response["tool_calls"]:
                    tool_name = tool_call["function"]["name"]
                    tool_args = tool_call["function"]["arguments"]

                    logger.info(
                        "tool_call",
                        task_id=task_id,
                        tool=tool_name,
                        iteration=iteration,
                    )

                    tool_result = await self.tools.execute(tool_name, tool_args)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": str(tool_result),
                    })
            else:
                # LLM gave a final answer
                return response.get("content", "Task completed.")

        return "Task completed (max iterations reached)."

    def _build_system_prompt(self, task: dict) -> str:
        available_tool_names = ", ".join(
            self.tools.get_tool_names(task.get("required_tools", []))
        )

        return f"""You are a White-Ops AI agent. You perform professional white-collar tasks
accurately and efficiently.

Available tools: {available_tool_names}

Rules:
- Complete the task thoroughly and professionally
- Use the appropriate tools for the job
- Report your progress and results clearly
- If you encounter an error, explain what went wrong
- Save all output files to the shared storage"""

    def _build_user_prompt(self, task: dict) -> str:
        parts = [f"Task: {task.get('title', 'Untitled')}"]
        if task.get("description"):
            parts.append(f"\nDescription: {task['description']}")
        if task.get("instructions"):
            parts.append(f"\nInstructions: {task['instructions']}")
        return "\n".join(parts)

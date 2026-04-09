"""Task executor - runs tasks using LLM and tools with parallel execution support."""

import asyncio
import traceback
from datetime import datetime, timezone

import httpx
import structlog

from agent.llm.provider import LLMProvider
from agent.tools.registry import ToolRegistry

logger = structlog.get_logger()

# Limits
DEFAULT_MAX_ITERATIONS = 20
ABSOLUTE_MAX_ITERATIONS = 50
DEFAULT_TOOL_TIMEOUT = 30  # seconds
MAX_OUTPUT_BYTES = 50 * 1024  # 50KB
APPROVAL_WAIT_TIMEOUT = 300  # 5 minutes

DANGEROUS_TOOLS = {
    "shell", "docker_ops", "terraform", "code_exec", "file_manager",
    "database", "ssh_manager", "git_ops",
}
READ_ONLY_TOOLS = {
    "search", "browser", "web_scraper", "rss_feed", "health_checker",
    "prometheus", "log_analyzer", "text_summarizer",
}


def _truncate_output(output: str) -> str:
    """Truncate tool output to 50KB max."""
    if len(output) > MAX_OUTPUT_BYTES:
        return output[:MAX_OUTPUT_BYTES] + "\n... [output truncated at 50KB]"
    return output


class TaskExecutor:
    _tool_semaphore = asyncio.Semaphore(5)

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

            # Get configurable max_iterations from task metadata
            metadata = task.get("metadata", {}) or {}
            max_iterations = min(
                metadata.get("max_iterations", DEFAULT_MAX_ITERATIONS),
                ABSOLUTE_MAX_ITERATIONS,
            )

            # Get per-tool timeout from metadata
            tool_timeout = metadata.get("tool_timeout", DEFAULT_TOOL_TIMEOUT)

            # Build agent config for autonomy checks
            agent_config = {
                "autonomy_level": task.get("agent", {}).get("autonomy_level", "autonomous") if isinstance(task.get("agent"), dict) else metadata.get("autonomy_level", "autonomous"),
                "tool_blacklist": task.get("agent", {}).get("tool_blacklist", []) if isinstance(task.get("agent"), dict) else metadata.get("tool_blacklist", []),
                "risk_rules": task.get("agent", {}).get("risk_rules", {}) if isinstance(task.get("agent"), dict) else metadata.get("risk_rules", {}),
            }

            # Run the LLM agent loop
            result = await self._agent_loop(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                tools=available_tools,
                task_id=task_id,
                max_iterations=max_iterations,
                tool_timeout=tool_timeout,
                agent_config=agent_config,
                client=client,
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

    async def _check_autonomy(self, tool_name: str, tool_args: dict, agent_config: dict) -> dict:
        """Check if tool execution is allowed by autonomy settings."""
        level = agent_config.get("autonomy_level", "autonomous")

        if level == "read_only" and tool_name not in READ_ONLY_TOOLS:
            return {"allowed": False, "reason": f"Agent is in READ_ONLY mode. Tool '{tool_name}' is blocked."}

        if level == "supervised":
            return {"allowed": False, "needs_approval": True, "reason": f"Agent requires approval for all tools. Awaiting approval for '{tool_name}'."}

        if level == "cautious" and tool_name in DANGEROUS_TOOLS:
            return {"allowed": False, "needs_approval": True, "reason": f"Tool '{tool_name}' requires approval in CAUTIOUS mode."}

        # Check tool blacklist
        blacklist = agent_config.get("tool_blacklist", [])
        if tool_name in blacklist:
            return {"allowed": False, "reason": f"Tool '{tool_name}' is blacklisted for this agent."}

        # Check risk rules
        risk_rules = agent_config.get("risk_rules", {})
        require_approval_for = risk_rules.get("require_approval_for", [])
        if tool_name in require_approval_for:
            return {"allowed": False, "needs_approval": True, "reason": f"Tool '{tool_name}' requires approval per risk rules."}

        if risk_rules.get("block_external_api") and tool_name in {"api_caller", "webhook"}:
            return {"allowed": False, "reason": f"External API calls are blocked for this agent. Tool '{tool_name}' denied."}

        return {"allowed": True}

    async def _request_approval(self, tool_name: str, tool_args: dict, task_id: str, client: httpx.AsyncClient) -> bool:
        """Post an approval request to the master server and wait for response."""
        try:
            resp = await client.post(
                "/api/v1/approvals/",
                json={
                    "task_id": task_id,
                    "action": f"execute_tool:{tool_name}",
                    "details": {"tool_name": tool_name, "tool_args": tool_args},
                },
            )
            if resp.status_code != 200:
                logger.warning("approval_request_failed", tool=tool_name, status=resp.status_code)
                return False

            approval_id = resp.json().get("id")
            if not approval_id:
                return False

            # Poll for approval status with timeout
            deadline = asyncio.get_event_loop().time() + APPROVAL_WAIT_TIMEOUT
            while asyncio.get_event_loop().time() < deadline:
                check = await client.get(f"/api/v1/approvals/{approval_id}")
                if check.status_code == 200:
                    status = check.json().get("status")
                    if status == "approved":
                        logger.info("tool_approved", tool=tool_name, approval_id=approval_id)
                        return True
                    if status in ("rejected", "denied"):
                        logger.info("tool_rejected", tool=tool_name, approval_id=approval_id)
                        return False
                await asyncio.sleep(2)

            logger.warning("approval_timeout", tool=tool_name, approval_id=approval_id)
            return False
        except Exception as e:
            logger.error("approval_request_error", tool=tool_name, error=str(e))
            return False

    async def _execute_tool_with_timeout(
        self,
        tool_name: str,
        tool_args: dict,
        timeout: float,
    ) -> str:
        """Execute a single tool with a timeout."""
        try:
            result = await asyncio.wait_for(
                self.tools.execute(tool_name, tool_args),
                timeout=timeout,
            )
            return _truncate_output(str(result))
        except asyncio.TimeoutError:
            logger.warning("tool_timeout", tool=tool_name, timeout=timeout)
            return f"Error: Tool '{tool_name}' timed out after {timeout}s"
        except Exception as e:
            logger.error("tool_execution_error", tool=tool_name, error=str(e))
            return f"Error executing {tool_name}: {e}"

    async def _execute_tools_parallel(
        self,
        tool_calls: list[dict],
        task_id: str,
        iteration: int,
        tool_timeout: float,
        agent_config: dict | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> list[dict]:
        """Execute multiple tool calls in parallel using asyncio.gather.

        Independent tool calls (from the same LLM response) are executed
        concurrently for better performance.
        """
        async def run_tool(tool_call: dict) -> dict:
            async with self._tool_semaphore:
                tool_name = tool_call["function"]["name"]
                tool_args = tool_call["function"]["arguments"]

                # Autonomy check
                if agent_config:
                    check = await self._check_autonomy(tool_name, tool_args, agent_config)
                    if not check["allowed"]:
                        if check.get("needs_approval") and client:
                            approved = await self._request_approval(tool_name, tool_args, task_id, client)
                            if not approved:
                                return {
                                    "role": "tool",
                                    "tool_call_id": tool_call["id"],
                                    "content": f"BLOCKED: {check['reason']} Approval was denied or timed out.",
                                }
                        else:
                            return {
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "content": f"BLOCKED: {check['reason']}",
                            }

                logger.info(
                    "tool_call",
                    task_id=task_id,
                    tool=tool_name,
                    iteration=iteration,
                )

                result = await self._execute_tool_with_timeout(
                    tool_name, tool_args, tool_timeout
                )

                return {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": result,
                }

        # Execute all tool calls concurrently
        results = await asyncio.gather(
            *(run_tool(tc) for tc in tool_calls),
            return_exceptions=True,
        )

        # Handle any exceptions from gather
        messages = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                tool_name = tool_calls[i]["function"]["name"]
                logger.error(
                    "parallel_tool_error",
                    tool=tool_name,
                    error=str(result),
                )
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_calls[i]["id"],
                    "content": f"Error executing {tool_name}: {result}",
                })
            else:
                messages.append(result)

        return messages

    async def _agent_loop(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict],
        task_id: str,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        tool_timeout: float = DEFAULT_TOOL_TIMEOUT,
        agent_config: dict | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> str:
        """Run the LLM agent loop with tool calling and parallel execution."""
        messages = [{"role": "user", "content": user_prompt}]

        for iteration in range(max_iterations):
            response = await self.llm.chat(
                system=system_prompt,
                messages=messages,
                tools=tools if tools else None,
            )

            # Check if the LLM wants to call tools
            if response.get("tool_calls"):
                messages.append({
                    "role": "assistant",
                    "content": response.get("content", ""),
                    "tool_calls": response["tool_calls"],
                })

                tool_calls = response["tool_calls"]

                if len(tool_calls) == 1:
                    # Single tool call -- execute directly
                    tc = tool_calls[0]
                    tool_name = tc["function"]["name"]
                    tool_args = tc["function"]["arguments"]

                    # Autonomy check
                    if agent_config:
                        check = await self._check_autonomy(tool_name, tool_args, agent_config)
                        if not check["allowed"]:
                            if check.get("needs_approval") and client:
                                approved = await self._request_approval(tool_name, tool_args, task_id, client)
                                if not approved:
                                    messages.append({
                                        "role": "tool",
                                        "tool_call_id": tc["id"],
                                        "content": f"BLOCKED: {check['reason']} Approval was denied or timed out.",
                                    })
                                    continue
                            else:
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tc["id"],
                                    "content": f"BLOCKED: {check['reason']}",
                                })
                                continue

                    logger.info(
                        "tool_call",
                        task_id=task_id,
                        tool=tool_name,
                        iteration=iteration,
                    )

                    tool_result = await self._execute_tool_with_timeout(
                        tool_name, tool_args, tool_timeout
                    )

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": tool_result,
                    })
                else:
                    # Multiple tool calls -- execute in parallel
                    logger.info(
                        "parallel_tool_execution",
                        task_id=task_id,
                        tool_count=len(tool_calls),
                        iteration=iteration,
                    )

                    tool_messages = await self._execute_tools_parallel(
                        tool_calls, task_id, iteration, tool_timeout,
                        agent_config=agent_config, client=client,
                    )
                    messages.extend(tool_messages)
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
- Save all output files to the shared storage
- When multiple independent tool calls are needed, request them all at once for parallel execution"""

    def _build_user_prompt(self, task: dict) -> str:
        parts = [f"Task: {task.get('title', 'Untitled')}"]
        if task.get("description"):
            parts.append(f"\nDescription: {task['description']}")
        if task.get("instructions"):
            parts.append(f"\nInstructions: {task['instructions']}")
        return "\n".join(parts)

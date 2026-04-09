"""Terraform tool - manage infrastructure as code via Terraform CLI."""

import asyncio
import json
from pathlib import Path
from typing import Any

import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

MAX_OUTPUT_BYTES = 50 * 1024
INIT_TIMEOUT = 120  # seconds
PLAN_TIMEOUT = 300
APPLY_TIMEOUT = 600  # 10 minutes
DESTROY_TIMEOUT = 600


def _truncate(text: str) -> str:
    if len(text) > MAX_OUTPUT_BYTES:
        return text[:MAX_OUTPUT_BYTES] + "\n... [output truncated]"
    return text


class TerraformTool(BaseTool):
    name = "terraform"
    description = (
        "Manage infrastructure with Terraform. Supports init, plan, apply, destroy, "
        "output, and state list. CRITICAL: apply and destroy with auto_approve=true "
        "require explicit approval (returns needs_approval flag)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["init", "plan", "apply", "destroy", "output", "state_list"],
                "description": "Terraform action to perform.",
            },
            "working_dir": {
                "type": "string",
                "description": "Directory containing Terraform configuration.",
            },
            "vars": {
                "type": "object",
                "description": "Terraform variables as key-value pairs (for plan/apply).",
                "additionalProperties": {"type": "string"},
            },
            "auto_approve": {
                "type": "boolean",
                "description": "Auto-approve apply/destroy. Default: false. REQUIRES EXPLICIT APPROVAL.",
            },
        },
        "required": ["action", "working_dir"],
    }

    async def _run_terraform(
        self, args: list[str], working_dir: str, timeout: int
    ) -> tuple[int, str, str]:
        """Run a terraform command."""
        if not Path(working_dir).is_dir():
            raise FileNotFoundError(f"Working directory not found: {working_dir}")

        proc = await asyncio.create_subprocess_exec(
            "terraform", *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=working_dir,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return (
            proc.returncode or 0,
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
        )

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action")
        working_dir = kwargs.get("working_dir", "")
        logger.info("terraform_execute", action=action, working_dir=working_dir)

        if not working_dir:
            return json.dumps({"error": "working_dir is required"})

        try:
            if action == "init":
                return await self._init(working_dir)
            elif action == "plan":
                return await self._plan(working_dir, kwargs)
            elif action == "apply":
                return await self._apply(working_dir, kwargs)
            elif action == "destroy":
                return await self._destroy(working_dir, kwargs)
            elif action == "output":
                return await self._output(working_dir)
            elif action == "state_list":
                return await self._state_list(working_dir)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except FileNotFoundError as e:
            return json.dumps({"error": str(e)})
        except TimeoutError:
            logger.error("terraform_timeout", action=action)
            return json.dumps({"error": f"Terraform {action} timed out"})
        except Exception as e:
            logger.error("terraform_error", error=str(e))
            return json.dumps({"error": f"Terraform operation failed: {e}"})

    async def _init(self, working_dir: str) -> str:
        code, stdout, stderr = await self._run_terraform(
            ["init", "-no-color"], working_dir, INIT_TIMEOUT
        )
        output = stdout + stderr
        if code == 0:
            logger.info("terraform_init_done", working_dir=working_dir)
            return _truncate(json.dumps({"success": True, "output": output}))
        return _truncate(json.dumps({"error": output}))

    async def _plan(self, working_dir: str, kwargs: dict) -> str:
        args = ["plan", "-no-color"]
        vars_dict = kwargs.get("vars", {})
        for k, v in vars_dict.items():
            args.extend(["-var", f"{k}={v}"])

        code, stdout, stderr = await self._run_terraform(args, working_dir, PLAN_TIMEOUT)
        output = stdout + stderr
        if code == 0:
            logger.info("terraform_plan_done", working_dir=working_dir)
            return _truncate(json.dumps({"success": True, "plan_output": output}))
        return _truncate(json.dumps({"error": output}))

    async def _apply(self, working_dir: str, kwargs: dict) -> str:
        auto_approve = kwargs.get("auto_approve", False)

        if auto_approve:
            # CRITICAL: Return needs_approval flag for confirmation
            logger.warning("terraform_apply_auto_approve_requested", working_dir=working_dir)
            return json.dumps({
                "needs_approval": True,
                "action": "apply",
                "working_dir": working_dir,
                "message": (
                    "Terraform apply with auto_approve=true requires explicit approval. "
                    "This will modify real infrastructure. Please confirm."
                ),
            })

        # Without auto_approve, run plan only (show what would change)
        args = ["plan", "-no-color"]
        vars_dict = kwargs.get("vars", {})
        for k, v in vars_dict.items():
            args.extend(["-var", f"{k}={v}"])

        code, stdout, stderr = await self._run_terraform(args, working_dir, PLAN_TIMEOUT)
        output = stdout + stderr
        return _truncate(json.dumps({
            "success": code == 0,
            "message": "Plan generated. Set auto_approve=true to apply (requires approval).",
            "plan_output": output,
        }))

    async def _destroy(self, working_dir: str, kwargs: dict) -> str:
        auto_approve = kwargs.get("auto_approve", False)

        if auto_approve:
            # CRITICAL: Return needs_approval flag for confirmation
            logger.warning("terraform_destroy_auto_approve_requested", working_dir=working_dir)
            return json.dumps({
                "needs_approval": True,
                "action": "destroy",
                "working_dir": working_dir,
                "message": (
                    "Terraform destroy with auto_approve=true requires explicit approval. "
                    "This will DESTROY real infrastructure. Please confirm."
                ),
            })

        # Without auto_approve, show plan for destroy
        args = ["plan", "-destroy", "-no-color"]

        code, stdout, stderr = await self._run_terraform(args, working_dir, PLAN_TIMEOUT)
        output = stdout + stderr
        return _truncate(json.dumps({
            "success": code == 0,
            "message": "Destroy plan generated. Set auto_approve=true to destroy (requires approval).",
            "plan_output": output,
        }))

    async def _output(self, working_dir: str) -> str:
        code, stdout, stderr = await self._run_terraform(
            ["output", "-json", "-no-color"], working_dir, 30
        )
        if code != 0:
            return json.dumps({"error": (stdout + stderr).strip()})

        try:
            outputs = json.loads(stdout)
            result = {}
            for name, data in outputs.items():
                result[name] = {
                    "value": data.get("value"),
                    "type": data.get("type"),
                    "sensitive": data.get("sensitive", False),
                }
            return _truncate(json.dumps({"outputs": result}))
        except json.JSONDecodeError:
            return _truncate(json.dumps({"raw_output": stdout}))

    async def _state_list(self, working_dir: str) -> str:
        code, stdout, stderr = await self._run_terraform(
            ["state", "list"], working_dir, 30
        )
        if code != 0:
            return json.dumps({"error": (stdout + stderr).strip()})

        resources = [r.strip() for r in stdout.strip().split("\n") if r.strip()]
        logger.info("terraform_state_list", count=len(resources))
        return _truncate(json.dumps({"resources": resources, "count": len(resources)}))

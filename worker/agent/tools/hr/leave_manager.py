"""Leave manager tool - manage employee leave requests and balances."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

STORAGE_PATH = "/tmp/whiteops_leaves.json"
MAX_OUTPUT_BYTES = 50 * 1024

LEAVE_TYPES = ["annual", "sick", "personal"]
DEFAULT_BALANCES = {"annual": 20, "sick": 10, "personal": 5}


def _truncate(result: str) -> str:
    if len(result) > MAX_OUTPUT_BYTES:
        return result[:MAX_OUTPUT_BYTES] + "\n... [output truncated at 50KB]"
    return result


class LeaveManagerTool(BaseTool):
    name = "leave_manager"
    description = (
        "Manage employee leave requests: submit, approve, reject leave requests, "
        "check leave balances, and list requests by status. "
        "Leave types: annual (20 days), sick (10 days), personal (5 days). "
        "Data stored in /tmp/whiteops_leaves.json."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "request_leave",
                    "approve_leave",
                    "reject_leave",
                    "get_balance",
                    "list_requests",
                ],
                "description": "Leave management action.",
            },
            "employee_id": {
                "type": "string",
                "description": "Employee ID.",
            },
            "type": {
                "type": "string",
                "enum": LEAVE_TYPES,
                "description": "Type of leave.",
            },
            "start_date": {
                "type": "string",
                "description": "Leave start date (YYYY-MM-DD).",
            },
            "end_date": {
                "type": "string",
                "description": "Leave end date (YYYY-MM-DD).",
            },
            "reason": {
                "type": "string",
                "description": "Reason for leave or rejection.",
            },
            "request_id": {
                "type": "string",
                "description": "Leave request ID (for approve/reject).",
            },
            "status": {
                "type": "string",
                "enum": ["pending", "approved", "rejected"],
                "description": "Filter requests by status.",
            },
        },
        "required": ["action"],
    }

    def _load(self) -> dict:
        path = Path(STORAGE_PATH)
        if path.exists():
            return json.loads(path.read_text())
        return {"requests": [], "balances": {}}

    def _save(self, data: dict) -> None:
        Path(STORAGE_PATH).write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def _ensure_balance(self, data: dict, employee_id: str) -> dict:
        """Ensure employee has a balance record, creating default if needed."""
        if employee_id not in data["balances"]:
            data["balances"][employee_id] = dict(DEFAULT_BALANCES)
        return data["balances"][employee_id]

    def _count_business_days(self, start: str, end: str) -> int:
        """Count business days between two dates (inclusive)."""
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")
        days = 0
        current = start_dt
        while current <= end_dt:
            if current.weekday() < 5:  # Monday=0 to Friday=4
                days += 1
            current = current.replace(day=current.day)
            from datetime import timedelta
            current += timedelta(days=1)
        return days

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action", "")
        logger.info("leave_manager_execute", action=action)

        try:
            data = self._load()

            if action == "request_leave":
                return self._request_leave(data, kwargs)
            elif action == "approve_leave":
                return self._approve_leave(data, kwargs)
            elif action == "reject_leave":
                return self._reject_leave(data, kwargs)
            elif action == "get_balance":
                return self._get_balance(data, kwargs)
            elif action == "list_requests":
                return self._list_requests(data, kwargs)
            else:
                return _truncate(json.dumps({"error": f"Unknown action: {action}"}))
        except Exception as e:
            logger.error("leave_manager_failed", action=action, error=str(e))
            return _truncate(json.dumps({"error": f"Leave manager failed: {e}"}))

    def _request_leave(self, data: dict, kwargs: dict) -> str:
        employee_id = kwargs.get("employee_id", "")
        leave_type = kwargs.get("type", "")
        start_date = kwargs.get("start_date", "")
        end_date = kwargs.get("end_date", "")

        if not employee_id:
            return _truncate(json.dumps({"error": "'employee_id' is required"}))
        if not leave_type:
            return _truncate(json.dumps({"error": "'type' is required"}))
        if leave_type not in LEAVE_TYPES:
            return _truncate(json.dumps({"error": f"Invalid leave type. Must be one of: {LEAVE_TYPES}"}))
        if not start_date or not end_date:
            return _truncate(json.dumps({"error": "'start_date' and 'end_date' are required"}))

        # Validate dates
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return _truncate(json.dumps({"error": "Dates must be in YYYY-MM-DD format"}))

        if end_dt < start_dt:
            return _truncate(json.dumps({"error": "end_date must be on or after start_date"}))

        days = self._count_business_days(start_date, end_date)
        if days <= 0:
            return _truncate(json.dumps({"error": "No business days in the selected range"}))

        # Check balance
        balance = self._ensure_balance(data, employee_id)
        remaining = balance.get(leave_type, 0)
        if days > remaining:
            return _truncate(json.dumps({
                "error": f"Insufficient {leave_type} leave balance. Remaining: {remaining} days, requested: {days} days.",
            }))

        request = {
            "id": uuid4().hex[:8],
            "employee_id": employee_id,
            "type": leave_type,
            "start_date": start_date,
            "end_date": end_date,
            "business_days": days,
            "reason": kwargs.get("reason", ""),
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }

        data["requests"].append(request)
        self._save(data)

        logger.info("leave_requested", id=request["id"], employee=employee_id, type=leave_type, days=days)
        return _truncate(json.dumps({"success": True, "request": request}))

    def _approve_leave(self, data: dict, kwargs: dict) -> str:
        request_id = kwargs.get("request_id", "")
        if not request_id:
            return _truncate(json.dumps({"error": "'request_id' is required"}))

        for req in data["requests"]:
            if req["id"] == request_id:
                if req["status"] != "pending":
                    return _truncate(json.dumps({"error": f"Request is already {req['status']}"}))

                req["status"] = "approved"
                req["approved_at"] = datetime.now().isoformat()

                # Deduct balance
                employee_id = req["employee_id"]
                balance = self._ensure_balance(data, employee_id)
                balance[req["type"]] = max(0, balance[req["type"]] - req["business_days"])

                self._save(data)
                logger.info("leave_approved", id=request_id, employee=employee_id)
                return _truncate(json.dumps({
                    "success": True,
                    "request": req,
                    "remaining_balance": balance[req["type"]],
                }))

        return _truncate(json.dumps({"error": f"Request {request_id} not found"}))

    def _reject_leave(self, data: dict, kwargs: dict) -> str:
        request_id = kwargs.get("request_id", "")
        reason = kwargs.get("reason", "")

        if not request_id:
            return _truncate(json.dumps({"error": "'request_id' is required"}))

        for req in data["requests"]:
            if req["id"] == request_id:
                if req["status"] != "pending":
                    return _truncate(json.dumps({"error": f"Request is already {req['status']}"}))

                req["status"] = "rejected"
                req["rejected_at"] = datetime.now().isoformat()
                req["rejection_reason"] = reason

                self._save(data)
                logger.info("leave_rejected", id=request_id, reason=reason)
                return _truncate(json.dumps({"success": True, "request": req}))

        return _truncate(json.dumps({"error": f"Request {request_id} not found"}))

    def _get_balance(self, data: dict, kwargs: dict) -> str:
        employee_id = kwargs.get("employee_id", "")
        if not employee_id:
            return _truncate(json.dumps({"error": "'employee_id' is required"}))

        balance = self._ensure_balance(data, employee_id)
        self._save(data)

        # Calculate used days
        used = {t: DEFAULT_BALANCES[t] - balance.get(t, 0) for t in LEAVE_TYPES}

        # Count pending requests
        pending = [
            r for r in data["requests"]
            if r["employee_id"] == employee_id and r["status"] == "pending"
        ]
        pending_days = {t: 0 for t in LEAVE_TYPES}
        for r in pending:
            pending_days[r["type"]] += r.get("business_days", 0)

        logger.info("balance_checked", employee=employee_id)
        return _truncate(json.dumps({
            "employee_id": employee_id,
            "balances": balance,
            "used": used,
            "pending": pending_days,
            "defaults": DEFAULT_BALANCES,
        }))

    def _list_requests(self, data: dict, kwargs: dict) -> str:
        requests = data["requests"]
        status_filter = kwargs.get("status", "")
        employee_id = kwargs.get("employee_id", "")

        if status_filter:
            requests = [r for r in requests if r["status"] == status_filter]
        if employee_id:
            requests = [r for r in requests if r["employee_id"] == employee_id]

        # Sort by created_at descending
        requests = sorted(requests, key=lambda r: r.get("created_at", ""), reverse=True)

        logger.info("leave_requests_listed", count=len(requests))
        return _truncate(json.dumps({
            "requests": requests[:50],
            "count": len(requests),
            "filter": {"status": status_filter or "all", "employee_id": employee_id or "all"},
        }))

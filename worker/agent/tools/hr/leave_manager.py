"""Leave manager tool - manage employee leave requests."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from agent.tools.base import BaseTool

STORAGE_PATH = "/tmp/whiteops_leaves.json"


class LeaveManagerTool(BaseTool):
    name = "leave_manager"
    description = (
        "Manage employee leave requests: submit requests, approve/reject, "
        "list pending requests, and check leave balances."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["request_leave", "approve", "reject", "list_requests", "balance"],
                "description": "Action to perform.",
            },
            "employee_id": {
                "type": "string",
                "description": "Employee identifier.",
            },
            "employee_name": {
                "type": "string",
                "description": "Employee name.",
            },
            "leave_type": {
                "type": "string",
                "enum": ["annual", "sick", "unpaid", "maternity", "paternity", "bereavement", "marriage"],
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
                "description": "Reason for leave.",
            },
            "request_id": {
                "type": "string",
                "description": "Leave request ID (for approve/reject).",
            },
            "status_filter": {
                "type": "string",
                "enum": ["pending", "approved", "rejected", "all"],
                "description": "Filter by status (for list_requests).",
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

    def _default_balance(self) -> dict:
        return {"annual": 14, "sick": 10, "unpaid": 90, "maternity": 112, "paternity": 5, "bereavement": 3, "marriage": 3}

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]
        data = self._load()

        if action == "request_leave":
            emp_id = kwargs.get("employee_id")
            if not emp_id:
                return {"error": "employee_id is required."}
            leave_type = kwargs.get("leave_type", "annual")
            start = kwargs.get("start_date")
            end = kwargs.get("end_date")
            if not start or not end:
                return {"error": "start_date and end_date are required."}

            start_dt = datetime.strptime(start, "%Y-%m-%d")
            end_dt = datetime.strptime(end, "%Y-%m-%d")
            days = (end_dt - start_dt).days + 1
            if days <= 0:
                return {"error": "end_date must be after start_date."}

            # Check balance
            if emp_id not in data["balances"]:
                data["balances"][emp_id] = self._default_balance()
            remaining = data["balances"][emp_id].get(leave_type, 0)
            if days > remaining:
                return {"error": f"Insufficient {leave_type} leave balance. Remaining: {remaining} days, requested: {days} days."}

            request = {
                "id": uuid4().hex[:8],
                "employee_id": emp_id,
                "employee_name": kwargs.get("employee_name", ""),
                "leave_type": leave_type,
                "start_date": start,
                "end_date": end,
                "days": days,
                "reason": kwargs.get("reason", ""),
                "status": "pending",
                "created_at": datetime.now().isoformat(),
            }
            data["requests"].append(request)
            self._save(data)
            return {"message": "Leave request submitted.", "request": request}

        elif action == "approve":
            req_id = kwargs.get("request_id")
            if not req_id:
                return {"error": "request_id is required."}
            for req in data["requests"]:
                if req["id"] == req_id:
                    if req["status"] != "pending":
                        return {"error": f"Request is already {req['status']}."}
                    req["status"] = "approved"
                    req["approved_at"] = datetime.now().isoformat()
                    # Deduct balance
                    emp_id = req["employee_id"]
                    if emp_id not in data["balances"]:
                        data["balances"][emp_id] = self._default_balance()
                    data["balances"][emp_id][req["leave_type"]] -= req["days"]
                    self._save(data)
                    return {"message": "Leave approved.", "request": req}
            return {"error": f"Request {req_id} not found."}

        elif action == "reject":
            req_id = kwargs.get("request_id")
            if not req_id:
                return {"error": "request_id is required."}
            for req in data["requests"]:
                if req["id"] == req_id:
                    if req["status"] != "pending":
                        return {"error": f"Request is already {req['status']}."}
                    req["status"] = "rejected"
                    req["rejected_at"] = datetime.now().isoformat()
                    self._save(data)
                    return {"message": "Leave rejected.", "request": req}
            return {"error": f"Request {req_id} not found."}

        elif action == "list_requests":
            requests = data["requests"]
            status_filter = kwargs.get("status_filter", "all")
            if status_filter != "all":
                requests = [r for r in requests if r["status"] == status_filter]
            if kwargs.get("employee_id"):
                requests = [r for r in requests if r["employee_id"] == kwargs["employee_id"]]
            return {"requests": requests, "count": len(requests)}

        elif action == "balance":
            emp_id = kwargs.get("employee_id")
            if not emp_id:
                return {"error": "employee_id is required."}
            if emp_id not in data["balances"]:
                data["balances"][emp_id] = self._default_balance()
                self._save(data)
            return {"employee_id": emp_id, "balances": data["balances"][emp_id]}

        return {"error": f"Unknown action: {action}"}

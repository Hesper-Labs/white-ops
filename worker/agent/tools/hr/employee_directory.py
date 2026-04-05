"""Employee directory tool - manage employee records."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from agent.tools.base import BaseTool

STORAGE_PATH = "/tmp/whiteops_employees.json"


class EmployeeDirectoryTool(BaseTool):
    name = "employee_directory"
    description = (
        "Manage an employee directory: add, search, list, update employees, "
        "and generate an organizational chart."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "search", "list", "update", "org_chart"],
                "description": "Action to perform.",
            },
            "employee_id": {
                "type": "string",
                "description": "Employee ID (for update).",
            },
            "name": {
                "type": "string",
                "description": "Full name of the employee.",
            },
            "email": {
                "type": "string",
                "description": "Email address.",
            },
            "phone": {
                "type": "string",
                "description": "Phone number.",
            },
            "department": {
                "type": "string",
                "description": "Department name.",
            },
            "title": {
                "type": "string",
                "description": "Job title.",
            },
            "manager_id": {
                "type": "string",
                "description": "ID of the employee's manager.",
            },
            "start_date": {
                "type": "string",
                "description": "Employment start date (YYYY-MM-DD).",
            },
            "query": {
                "type": "string",
                "description": "Search query (searches name, email, department, title).",
            },
            "updates": {
                "type": "object",
                "description": "Fields to update (for update action).",
            },
        },
        "required": ["action"],
    }

    def _load(self) -> list[dict]:
        path = Path(STORAGE_PATH)
        if path.exists():
            return json.loads(path.read_text())
        return []

    def _save(self, employees: list[dict]) -> None:
        Path(STORAGE_PATH).write_text(json.dumps(employees, indent=2, ensure_ascii=False))

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]
        employees = self._load()

        if action == "add":
            name = kwargs.get("name")
            if not name:
                return {"error": "name is required."}
            employee = {
                "id": uuid4().hex[:8],
                "name": name,
                "email": kwargs.get("email", ""),
                "phone": kwargs.get("phone", ""),
                "department": kwargs.get("department", ""),
                "title": kwargs.get("title", ""),
                "manager_id": kwargs.get("manager_id", ""),
                "start_date": kwargs.get("start_date", datetime.now().strftime("%Y-%m-%d")),
                "created_at": datetime.now().isoformat(),
            }
            employees.append(employee)
            self._save(employees)
            return {"message": "Employee added.", "employee": employee}

        elif action == "search":
            query = kwargs.get("query", "").lower()
            if not query:
                return {"error": "query is required for search."}
            results = [
                e for e in employees
                if query in e.get("name", "").lower()
                or query in e.get("email", "").lower()
                or query in e.get("department", "").lower()
                or query in e.get("title", "").lower()
            ]
            return {"results": results, "count": len(results)}

        elif action == "list":
            dept = kwargs.get("department")
            if dept:
                employees = [e for e in employees if e.get("department", "").lower() == dept.lower()]
            return {"employees": employees, "count": len(employees)}

        elif action == "update":
            emp_id = kwargs.get("employee_id")
            updates = kwargs.get("updates", {})
            if not emp_id:
                return {"error": "employee_id is required."}
            for emp in employees:
                if emp["id"] == emp_id:
                    for key, value in updates.items():
                        if key not in ("id", "created_at"):
                            emp[key] = value
                    emp["updated_at"] = datetime.now().isoformat()
                    self._save(employees)
                    return {"message": "Employee updated.", "employee": emp}
            return {"error": f"Employee {emp_id} not found."}

        elif action == "org_chart":
            # Build tree from manager_id relationships
            by_id = {e["id"]: e for e in employees}
            roots = []
            children_map: dict[str, list] = {}

            for emp in employees:
                mgr = emp.get("manager_id", "")
                if mgr and mgr in by_id:
                    children_map.setdefault(mgr, []).append(emp["id"])
                else:
                    roots.append(emp["id"])

            def build_node(emp_id: str, depth: int = 0) -> dict:
                emp = by_id[emp_id]
                node = {
                    "id": emp["id"],
                    "name": emp["name"],
                    "title": emp.get("title", ""),
                    "department": emp.get("department", ""),
                    "level": depth,
                    "reports": [],
                }
                for child_id in children_map.get(emp_id, []):
                    node["reports"].append(build_node(child_id, depth + 1))
                return node

            chart = [build_node(r) for r in roots]
            return {"org_chart": chart}

        return {"error": f"Unknown action: {action}"}

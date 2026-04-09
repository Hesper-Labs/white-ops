"""Employee directory tool - manage employee records and org charts."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

STORAGE_PATH = "/tmp/whiteops_employees.json"
MAX_OUTPUT_BYTES = 50 * 1024


def _truncate(result: str) -> str:
    if len(result) > MAX_OUTPUT_BYTES:
        return result[:MAX_OUTPUT_BYTES] + "\n... [output truncated at 50KB]"
    return result


class EmployeeDirectoryTool(BaseTool):
    name = "employee_directory"
    description = (
        "Manage an employee directory: add, list, get, update employees, "
        "and generate organizational charts by department. "
        "Data stored in /tmp/whiteops_employees.json."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add_employee", "list_employees", "get_employee", "update_employee", "org_chart"],
                "description": "Employee directory action.",
            },
            "name": {
                "type": "string",
                "description": "Employee full name.",
            },
            "email": {
                "type": "string",
                "description": "Employee email address.",
            },
            "department": {
                "type": "string",
                "description": "Department name.",
            },
            "title": {
                "type": "string",
                "description": "Job title.",
            },
            "manager": {
                "type": "string",
                "description": "Manager's employee ID.",
            },
            "start_date": {
                "type": "string",
                "description": "Employment start date (YYYY-MM-DD).",
            },
            "employee_id": {
                "type": "string",
                "description": "Employee ID (for get, update).",
            },
            "updates": {
                "type": "object",
                "description": "Fields to update.",
            },
            "search": {
                "type": "string",
                "description": "Search query (name, email, title, department).",
            },
        },
        "required": ["action"],
    }

    def _load(self) -> dict:
        path = Path(STORAGE_PATH)
        if path.exists():
            return json.loads(path.read_text())
        return {"employees": {}, "next_id": 1}

    def _save(self, data: dict) -> None:
        Path(STORAGE_PATH).write_text(json.dumps(data, indent=2, ensure_ascii=False))

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action", "")
        logger.info("employee_directory_execute", action=action)

        try:
            db = self._load()

            if action == "add_employee":
                return self._add_employee(db, kwargs)
            elif action == "list_employees":
                return self._list_employees(db, kwargs)
            elif action == "get_employee":
                return self._get_employee(db, kwargs)
            elif action == "update_employee":
                return self._update_employee(db, kwargs)
            elif action == "org_chart":
                return self._org_chart(db, kwargs)
            else:
                return _truncate(json.dumps({"error": f"Unknown action: {action}"}))
        except Exception as e:
            logger.error("employee_directory_failed", action=action, error=str(e))
            return _truncate(json.dumps({"error": f"Employee directory failed: {e}"}))

    def _add_employee(self, db: dict, kwargs: dict) -> str:
        name = kwargs.get("name", "")
        email = kwargs.get("email", "")
        department = kwargs.get("department", "")
        title = kwargs.get("title", "")

        if not name:
            return _truncate(json.dumps({"error": "'name' is required"}))
        if not email:
            return _truncate(json.dumps({"error": "'email' is required"}))
        if not department:
            return _truncate(json.dumps({"error": "'department' is required"}))
        if not title:
            return _truncate(json.dumps({"error": "'title' is required"}))

        eid = uuid4().hex[:8]
        employee = {
            "id": eid,
            "name": name,
            "email": email,
            "department": department,
            "title": title,
            "manager": kwargs.get("manager", ""),
            "start_date": kwargs.get("start_date", datetime.now().strftime("%Y-%m-%d")),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        db["employees"][eid] = employee
        self._save(db)

        logger.info("employee_added", id=eid, name=name, department=department)
        return _truncate(json.dumps({"success": True, "employee": employee}))

    def _list_employees(self, db: dict, kwargs: dict) -> str:
        employees = list(db["employees"].values())
        department = kwargs.get("department", "")
        search = kwargs.get("search", "").lower()

        if department:
            employees = [
                e for e in employees
                if e.get("department", "").lower() == department.lower()
            ]

        if search:
            employees = [
                e for e in employees
                if search in e.get("name", "").lower()
                or search in e.get("email", "").lower()
                or search in e.get("title", "").lower()
                or search in e.get("department", "").lower()
            ]

        logger.info("employees_listed", count=len(employees))
        return _truncate(json.dumps({"employees": employees[:50], "count": len(employees)}))

    def _get_employee(self, db: dict, kwargs: dict) -> str:
        employee_id = kwargs.get("employee_id", "")
        if not employee_id:
            return _truncate(json.dumps({"error": "'employee_id' is required"}))

        if employee_id not in db["employees"]:
            return _truncate(json.dumps({"error": f"Employee {employee_id} not found"}))

        employee = db["employees"][employee_id]

        # Add manager info if available
        if employee.get("manager") and employee["manager"] in db["employees"]:
            manager = db["employees"][employee["manager"]]
            employee["manager_name"] = manager.get("name", "")

        # Find direct reports
        direct_reports = [
            {"id": e["id"], "name": e["name"], "title": e.get("title", "")}
            for e in db["employees"].values()
            if e.get("manager") == employee_id
        ]
        employee["direct_reports"] = direct_reports

        logger.info("employee_retrieved", id=employee_id)
        return _truncate(json.dumps({"employee": employee}))

    def _update_employee(self, db: dict, kwargs: dict) -> str:
        employee_id = kwargs.get("employee_id", "")
        updates = kwargs.get("updates", {})

        if not employee_id:
            return _truncate(json.dumps({"error": "'employee_id' is required"}))
        if not updates:
            return _truncate(json.dumps({"error": "'updates' object is required"}))
        if employee_id not in db["employees"]:
            return _truncate(json.dumps({"error": f"Employee {employee_id} not found"}))

        protected = {"id", "created_at"}
        for key, value in updates.items():
            if key not in protected:
                db["employees"][employee_id][key] = value
        db["employees"][employee_id]["updated_at"] = datetime.now().isoformat()

        self._save(db)
        logger.info("employee_updated", id=employee_id)
        return _truncate(json.dumps({"success": True, "employee": db["employees"][employee_id]}))

    def _org_chart(self, db: dict, kwargs: dict) -> str:
        department = kwargs.get("department", "")
        employees = list(db["employees"].values())

        if department:
            employees = [
                e for e in employees
                if e.get("department", "").lower() == department.lower()
            ]

        by_id = {e["id"]: e for e in employees}
        all_by_id = {e["id"]: e for e in db["employees"].values()}

        # Find roots (no manager or manager not in filtered set)
        roots = []
        children_map: dict[str, list] = {}

        for emp in employees:
            mgr = emp.get("manager", "")
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

        # Department summary
        departments: dict[str, int] = {}
        for emp in employees:
            dept = emp.get("department", "Unknown")
            departments[dept] = departments.get(dept, 0) + 1

        logger.info("org_chart_generated", employees=len(employees), departments=len(departments))
        return _truncate(json.dumps({
            "org_chart": chart,
            "total_employees": len(employees),
            "departments": departments,
            "filter": department or "all",
        }))

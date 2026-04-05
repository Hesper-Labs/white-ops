"""Project tracker tool - track projects and milestones."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from agent.tools.base import BaseTool

STORAGE_PATH = "/tmp/whiteops_projects.json"


class ProjectTrackerTool(BaseTool):
    name = "project_tracker"
    description = (
        "Track projects and milestones: create projects, add milestones, "
        "update progress, list projects, and generate project reports."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create_project", "add_milestone", "update_progress", "list_projects", "report"],
                "description": "Action to perform.",
            },
            "project_id": {
                "type": "string",
                "description": "Project ID.",
            },
            "name": {
                "type": "string",
                "description": "Project or milestone name.",
            },
            "description": {
                "type": "string",
                "description": "Project or milestone description.",
            },
            "start_date": {
                "type": "string",
                "description": "Start date (YYYY-MM-DD).",
            },
            "end_date": {
                "type": "string",
                "description": "End/due date (YYYY-MM-DD).",
            },
            "status": {
                "type": "string",
                "enum": ["not_started", "in_progress", "completed", "on_hold", "cancelled"],
                "description": "Project or milestone status.",
            },
            "progress": {
                "type": "number",
                "description": "Progress percentage (0-100).",
            },
            "milestone_id": {
                "type": "string",
                "description": "Milestone ID (for update_progress).",
            },
            "owner": {
                "type": "string",
                "description": "Project owner or responsible person.",
            },
            "budget": {
                "type": "number",
                "description": "Project budget.",
            },
        },
        "required": ["action"],
    }

    def _load(self) -> list[dict]:
        path = Path(STORAGE_PATH)
        if path.exists():
            return json.loads(path.read_text())
        return []

    def _save(self, projects: list[dict]) -> None:
        Path(STORAGE_PATH).write_text(json.dumps(projects, indent=2, ensure_ascii=False))

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]
        projects = self._load()

        if action == "create_project":
            name = kwargs.get("name")
            if not name:
                return {"error": "name is required."}
            project = {
                "id": uuid4().hex[:8],
                "name": name,
                "description": kwargs.get("description", ""),
                "owner": kwargs.get("owner", ""),
                "status": kwargs.get("status", "not_started"),
                "progress": kwargs.get("progress", 0),
                "start_date": kwargs.get("start_date", datetime.now().strftime("%Y-%m-%d")),
                "end_date": kwargs.get("end_date", ""),
                "budget": kwargs.get("budget", 0),
                "milestones": [],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            projects.append(project)
            self._save(projects)
            return {"message": "Project created.", "project": project}

        elif action == "add_milestone":
            project_id = kwargs.get("project_id")
            name = kwargs.get("name")
            if not project_id or not name:
                return {"error": "project_id and name are required."}
            for proj in projects:
                if proj["id"] == project_id:
                    milestone = {
                        "id": uuid4().hex[:8],
                        "name": name,
                        "description": kwargs.get("description", ""),
                        "status": kwargs.get("status", "not_started"),
                        "progress": kwargs.get("progress", 0),
                        "due_date": kwargs.get("end_date", ""),
                        "created_at": datetime.now().isoformat(),
                    }
                    proj["milestones"].append(milestone)
                    proj["updated_at"] = datetime.now().isoformat()
                    self._save(projects)
                    return {"message": "Milestone added.", "milestone": milestone}
            return {"error": f"Project {project_id} not found."}

        elif action == "update_progress":
            project_id = kwargs.get("project_id")
            if not project_id:
                return {"error": "project_id is required."}
            for proj in projects:
                if proj["id"] == project_id:
                    milestone_id = kwargs.get("milestone_id")
                    if milestone_id:
                        for ms in proj["milestones"]:
                            if ms["id"] == milestone_id:
                                if "progress" in kwargs:
                                    ms["progress"] = kwargs["progress"]
                                if "status" in kwargs:
                                    ms["status"] = kwargs["status"]
                                break
                        else:
                            return {"error": f"Milestone {milestone_id} not found."}
                    # Update project level
                    if "progress" in kwargs and not milestone_id:
                        proj["progress"] = kwargs["progress"]
                    if "status" in kwargs and not milestone_id:
                        proj["status"] = kwargs["status"]
                    # Auto-calculate project progress from milestones if they exist
                    if proj["milestones"] and not kwargs.get("progress"):
                        avg = sum(m["progress"] for m in proj["milestones"]) / len(proj["milestones"])
                        proj["progress"] = round(avg, 1)
                    proj["updated_at"] = datetime.now().isoformat()
                    self._save(projects)
                    return {"message": "Progress updated.", "project": proj}
            return {"error": f"Project {project_id} not found."}

        elif action == "list_projects":
            status = kwargs.get("status")
            if status:
                projects = [p for p in projects if p["status"] == status]
            summaries = [
                {
                    "id": p["id"],
                    "name": p["name"],
                    "status": p["status"],
                    "progress": p["progress"],
                    "owner": p.get("owner", ""),
                    "milestones_count": len(p.get("milestones", [])),
                    "end_date": p.get("end_date", ""),
                }
                for p in projects
            ]
            return {"projects": summaries, "count": len(summaries)}

        elif action == "report":
            project_id = kwargs.get("project_id")
            if project_id:
                for proj in projects:
                    if proj["id"] == project_id:
                        milestones = proj.get("milestones", [])
                        completed = [m for m in milestones if m["status"] == "completed"]
                        overdue = []
                        today = datetime.now().strftime("%Y-%m-%d")
                        for m in milestones:
                            if m.get("due_date") and m["due_date"] < today and m["status"] != "completed":
                                overdue.append(m)
                        return {
                            "project": proj,
                            "total_milestones": len(milestones),
                            "completed_milestones": len(completed),
                            "overdue_milestones": len(overdue),
                            "overdue_details": overdue,
                        }
                return {"error": f"Project {project_id} not found."}

            # Summary across all projects
            total = len(projects)
            by_status: dict[str, int] = {}
            for p in projects:
                by_status[p["status"]] = by_status.get(p["status"], 0) + 1
            avg_progress = round(sum(p["progress"] for p in projects) / total, 1) if total else 0
            return {
                "total_projects": total,
                "by_status": by_status,
                "average_progress": avg_progress,
            }

        return {"error": f"Unknown action: {action}"}

"""CRM tool - manage contacts, companies, and interactions."""

import json
from pathlib import Path
from typing import Any
from datetime import datetime

from agent.tools.base import BaseTool

# Simple file-based CRM storage
CRM_FILE = "/tmp/whiteops_crm.json"


class CRMTool(BaseTool):
    name = "crm"
    description = (
        "Manage contacts, companies, and interaction history. "
        "Add, search, update contacts and log interactions."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add_contact", "search", "update", "log_interaction", "list", "get"],
            },
            "contact": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "company": {"type": "string"},
                    "role": {"type": "string"},
                    "notes": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
            },
            "query": {"type": "string", "description": "Search query"},
            "contact_id": {"type": "string"},
            "interaction": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["email", "call", "meeting", "note"]},
                    "summary": {"type": "string"},
                },
            },
        },
        "required": ["action"],
    }

    def _load(self) -> dict:
        if Path(CRM_FILE).exists():
            return json.loads(Path(CRM_FILE).read_text())
        return {"contacts": {}, "next_id": 1}

    def _save(self, data: dict) -> None:
        Path(CRM_FILE).write_text(json.dumps(data, indent=2))

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]
        db = self._load()

        if action == "add_contact":
            contact = kwargs.get("contact", {})
            cid = str(db["next_id"])
            db["next_id"] += 1
            contact["id"] = cid
            contact["created_at"] = datetime.now().isoformat()
            contact["interactions"] = []
            db["contacts"][cid] = contact
            self._save(db)
            return json.dumps({"id": cid, "name": contact.get("name"), "status": "added"})

        elif action == "search":
            query = kwargs.get("query", "").lower()
            results = []
            for c in db["contacts"].values():
                searchable = f"{c.get('name', '')} {c.get('email', '')} {c.get('company', '')} {c.get('notes', '')}".lower()
                if query in searchable:
                    results.append(c)
            return json.dumps(results[:20])

        elif action == "list":
            return json.dumps(list(db["contacts"].values())[:50])

        elif action == "get":
            cid = kwargs.get("contact_id", "")
            contact = db["contacts"].get(cid)
            return json.dumps(contact) if contact else "Contact not found"

        elif action == "update":
            cid = kwargs.get("contact_id", "")
            if cid not in db["contacts"]:
                return "Contact not found"
            updates = kwargs.get("contact", {})
            db["contacts"][cid].update(updates)
            self._save(db)
            return f"Contact {cid} updated"

        elif action == "log_interaction":
            cid = kwargs.get("contact_id", "")
            if cid not in db["contacts"]:
                return "Contact not found"
            interaction = kwargs.get("interaction", {})
            interaction["date"] = datetime.now().isoformat()
            db["contacts"][cid].setdefault("interactions", []).append(interaction)
            self._save(db)
            return f"Interaction logged for contact {cid}"

        return f"Unknown action: {action}"

"""CRM tool - manage contacts, deals, and sales pipeline."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

CRM_FILE = "/tmp/whiteops_crm.json"
MAX_OUTPUT_BYTES = 50 * 1024

PIPELINE_STAGES = ["lead", "qualified", "proposal", "negotiation", "closed_won", "closed_lost"]


def _truncate(result: str) -> str:
    if len(result) > MAX_OUTPUT_BYTES:
        return result[:MAX_OUTPUT_BYTES] + "\n... [output truncated at 50KB]"
    return result


class CRMTool(BaseTool):
    name = "crm"
    description = (
        "Manage contacts and deals in a CRM system. Add, list, update contacts "
        "and manage deals through a sales pipeline with stages: "
        "lead, qualified, proposal, negotiation, closed_won, closed_lost. "
        "Data stored in /tmp/whiteops_crm.json."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "add_contact",
                    "list_contacts",
                    "update_contact",
                    "add_deal",
                    "list_deals",
                    "update_deal",
                ],
                "description": "CRM action to perform.",
            },
            "name": {
                "type": "string",
                "description": "Contact name (for add_contact).",
            },
            "email": {
                "type": "string",
                "description": "Contact email (for add_contact).",
            },
            "company": {
                "type": "string",
                "description": "Company name.",
            },
            "phone": {
                "type": "string",
                "description": "Phone number.",
            },
            "notes": {
                "type": "string",
                "description": "Additional notes.",
            },
            "search": {
                "type": "string",
                "description": "Search query for listing contacts.",
            },
            "contact_id": {
                "type": "string",
                "description": "Contact ID (for update_contact, add_deal, list_deals).",
            },
            "updates": {
                "type": "object",
                "description": "Fields to update.",
            },
            "title": {
                "type": "string",
                "description": "Deal title (for add_deal).",
            },
            "value": {
                "type": "number",
                "description": "Deal value in currency (for add_deal).",
            },
            "stage": {
                "type": "string",
                "enum": PIPELINE_STAGES,
                "description": "Pipeline stage.",
            },
            "deal_id": {
                "type": "string",
                "description": "Deal ID (for update_deal, list_deals).",
            },
        },
        "required": ["action"],
    }

    def _load(self) -> dict:
        if Path(CRM_FILE).exists():
            return json.loads(Path(CRM_FILE).read_text())
        return {"contacts": {}, "deals": {}, "next_contact_id": 1, "next_deal_id": 1}

    def _save(self, data: dict) -> None:
        Path(CRM_FILE).write_text(json.dumps(data, indent=2, ensure_ascii=False))

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action", "")
        logger.info("crm_execute", action=action)

        try:
            db = self._load()

            if action == "add_contact":
                return self._add_contact(db, kwargs)
            elif action == "list_contacts":
                return self._list_contacts(db, kwargs)
            elif action == "update_contact":
                return self._update_contact(db, kwargs)
            elif action == "add_deal":
                return self._add_deal(db, kwargs)
            elif action == "list_deals":
                return self._list_deals(db, kwargs)
            elif action == "update_deal":
                return self._update_deal(db, kwargs)
            else:
                return _truncate(json.dumps({"error": f"Unknown action: {action}"}))
        except Exception as e:
            logger.error("crm_failed", action=action, error=str(e))
            return _truncate(json.dumps({"error": f"CRM operation failed: {e}"}))

    def _add_contact(self, db: dict, kwargs: dict) -> str:
        name = kwargs.get("name", "")
        email = kwargs.get("email", "")

        if not name:
            return _truncate(json.dumps({"error": "'name' is required"}))
        if not email:
            return _truncate(json.dumps({"error": "'email' is required"}))

        cid = str(db["next_contact_id"])
        db["next_contact_id"] += 1

        contact = {
            "id": cid,
            "name": name,
            "email": email,
            "company": kwargs.get("company", ""),
            "phone": kwargs.get("phone", ""),
            "notes": kwargs.get("notes", ""),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        db["contacts"][cid] = contact
        self._save(db)

        logger.info("crm_contact_added", id=cid, name=name)
        return _truncate(json.dumps({"success": True, "contact": contact}))

    def _list_contacts(self, db: dict, kwargs: dict) -> str:
        contacts = list(db["contacts"].values())
        search = kwargs.get("search", "").lower()
        company = kwargs.get("company", "").lower()

        if search:
            contacts = [
                c for c in contacts
                if search in c.get("name", "").lower()
                or search in c.get("email", "").lower()
                or search in c.get("company", "").lower()
                or search in c.get("notes", "").lower()
            ]

        if company:
            contacts = [
                c for c in contacts
                if company in c.get("company", "").lower()
            ]

        logger.info("crm_contacts_listed", count=len(contacts))
        return _truncate(json.dumps({"contacts": contacts[:50], "count": len(contacts)}))

    def _update_contact(self, db: dict, kwargs: dict) -> str:
        contact_id = kwargs.get("contact_id", "")
        updates = kwargs.get("updates", {})

        if not contact_id:
            return _truncate(json.dumps({"error": "'contact_id' is required"}))
        if not updates:
            return _truncate(json.dumps({"error": "'updates' object is required"}))

        if contact_id not in db["contacts"]:
            return _truncate(json.dumps({"error": f"Contact {contact_id} not found"}))

        protected = {"id", "created_at"}
        for key, value in updates.items():
            if key not in protected:
                db["contacts"][contact_id][key] = value
        db["contacts"][contact_id]["updated_at"] = datetime.now().isoformat()

        self._save(db)
        logger.info("crm_contact_updated", id=contact_id)
        return _truncate(json.dumps({"success": True, "contact": db["contacts"][contact_id]}))

    def _add_deal(self, db: dict, kwargs: dict) -> str:
        title = kwargs.get("title", "")
        value = kwargs.get("value", 0)
        contact_id = kwargs.get("contact_id", "")

        if not title:
            return _truncate(json.dumps({"error": "'title' is required"}))
        if not contact_id:
            return _truncate(json.dumps({"error": "'contact_id' is required"}))

        if contact_id not in db["contacts"]:
            return _truncate(json.dumps({"error": f"Contact {contact_id} not found"}))

        did = str(db["next_deal_id"])
        db["next_deal_id"] += 1

        stage = kwargs.get("stage", "lead")
        if stage not in PIPELINE_STAGES:
            return _truncate(json.dumps({"error": f"Invalid stage. Must be one of: {PIPELINE_STAGES}"}))

        deal = {
            "id": did,
            "title": title,
            "value": value,
            "contact_id": contact_id,
            "contact_name": db["contacts"][contact_id].get("name", ""),
            "stage": stage,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        db["deals"][did] = deal
        self._save(db)

        logger.info("crm_deal_added", id=did, title=title, value=value, stage=stage)
        return _truncate(json.dumps({"success": True, "deal": deal}))

    def _list_deals(self, db: dict, kwargs: dict) -> str:
        deals = list(db["deals"].values())
        stage = kwargs.get("stage", "")
        contact_id = kwargs.get("contact_id", "")

        if stage:
            deals = [d for d in deals if d.get("stage") == stage]
        if contact_id:
            deals = [d for d in deals if d.get("contact_id") == contact_id]

        # Calculate pipeline summary
        pipeline = {}
        total_value = 0
        for d in list(db["deals"].values()):
            s = d.get("stage", "lead")
            pipeline.setdefault(s, {"count": 0, "value": 0})
            pipeline[s]["count"] += 1
            pipeline[s]["value"] += d.get("value", 0)
            total_value += d.get("value", 0)

        logger.info("crm_deals_listed", count=len(deals))
        return _truncate(json.dumps({
            "deals": deals[:50],
            "count": len(deals),
            "pipeline_summary": pipeline,
            "total_pipeline_value": total_value,
        }))

    def _update_deal(self, db: dict, kwargs: dict) -> str:
        deal_id = kwargs.get("deal_id", "")
        updates = kwargs.get("updates", {})

        if not deal_id:
            return _truncate(json.dumps({"error": "'deal_id' is required"}))
        if not updates:
            return _truncate(json.dumps({"error": "'updates' object is required"}))

        if deal_id not in db["deals"]:
            return _truncate(json.dumps({"error": f"Deal {deal_id} not found"}))

        if "stage" in updates and updates["stage"] not in PIPELINE_STAGES:
            return _truncate(json.dumps({"error": f"Invalid stage. Must be one of: {PIPELINE_STAGES}"}))

        protected = {"id", "created_at"}
        for key, value in updates.items():
            if key not in protected:
                db["deals"][deal_id][key] = value
        db["deals"][deal_id]["updated_at"] = datetime.now().isoformat()

        self._save(db)
        logger.info("crm_deal_updated", id=deal_id)
        return _truncate(json.dumps({"success": True, "deal": db["deals"][deal_id]}))

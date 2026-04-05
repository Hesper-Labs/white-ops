"""Bookkeeping tool - track income and expenses."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from agent.tools.base import BaseTool

STORAGE_PATH = "/tmp/whiteops_bookkeeping.json"


class BookkeepingTool(BaseTool):
    name = "bookkeeping"
    description = (
        "Manage bookkeeping entries: add income/expense entries, list entries, "
        "check balance, generate report summaries, and categorize transactions."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add_entry", "list_entries", "balance", "report_summary", "categorize"],
                "description": "Action to perform.",
            },
            "entry_type": {
                "type": "string",
                "enum": ["income", "expense"],
                "description": "Type of entry (for add_entry).",
            },
            "amount": {
                "type": "number",
                "description": "Amount of the transaction.",
            },
            "category": {
                "type": "string",
                "description": "Category of the transaction.",
            },
            "description": {
                "type": "string",
                "description": "Description of the transaction.",
            },
            "date": {
                "type": "string",
                "description": "Date in YYYY-MM-DD format. Defaults to today.",
            },
            "entry_id": {
                "type": "string",
                "description": "Entry ID (for categorize action).",
            },
            "start_date": {
                "type": "string",
                "description": "Start date filter (YYYY-MM-DD).",
            },
            "end_date": {
                "type": "string",
                "description": "End date filter (YYYY-MM-DD).",
            },
        },
        "required": ["action"],
    }

    def _load(self) -> list[dict]:
        path = Path(STORAGE_PATH)
        if path.exists():
            return json.loads(path.read_text())
        return []

    def _save(self, entries: list[dict]) -> None:
        Path(STORAGE_PATH).write_text(json.dumps(entries, indent=2, ensure_ascii=False))

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]
        entries = self._load()

        if action == "add_entry":
            entry_type = kwargs.get("entry_type")
            amount = kwargs.get("amount")
            if not entry_type or amount is None:
                return {"error": "entry_type and amount are required for add_entry."}

            entry = {
                "id": uuid4().hex[:8],
                "type": entry_type,
                "amount": float(amount),
                "category": kwargs.get("category", "uncategorized"),
                "description": kwargs.get("description", ""),
                "date": kwargs.get("date", datetime.now().strftime("%Y-%m-%d")),
                "created_at": datetime.now().isoformat(),
            }
            entries.append(entry)
            self._save(entries)
            return {"message": "Entry added.", "entry": entry}

        elif action == "list_entries":
            filtered = entries
            if kwargs.get("start_date"):
                filtered = [e for e in filtered if e["date"] >= kwargs["start_date"]]
            if kwargs.get("end_date"):
                filtered = [e for e in filtered if e["date"] <= kwargs["end_date"]]
            if kwargs.get("category"):
                filtered = [e for e in filtered if e["category"] == kwargs["category"]]
            if kwargs.get("entry_type"):
                filtered = [e for e in filtered if e["type"] == kwargs["entry_type"]]
            return {"entries": filtered, "count": len(filtered)}

        elif action == "balance":
            income = sum(e["amount"] for e in entries if e["type"] == "income")
            expense = sum(e["amount"] for e in entries if e["type"] == "expense")
            return {
                "total_income": income,
                "total_expense": expense,
                "balance": income - expense,
            }

        elif action == "report_summary":
            start = kwargs.get("start_date")
            end = kwargs.get("end_date")
            filtered = entries
            if start:
                filtered = [e for e in filtered if e["date"] >= start]
            if end:
                filtered = [e for e in filtered if e["date"] <= end]

            income_by_cat: dict[str, float] = {}
            expense_by_cat: dict[str, float] = {}
            for e in filtered:
                bucket = income_by_cat if e["type"] == "income" else expense_by_cat
                bucket[e["category"]] = bucket.get(e["category"], 0) + e["amount"]

            total_income = sum(income_by_cat.values())
            total_expense = sum(expense_by_cat.values())

            return {
                "period": {"start": start or "all", "end": end or "all"},
                "total_income": total_income,
                "total_expense": total_expense,
                "net": total_income - total_expense,
                "income_by_category": income_by_cat,
                "expense_by_category": expense_by_cat,
                "entry_count": len(filtered),
            }

        elif action == "categorize":
            entry_id = kwargs.get("entry_id")
            category = kwargs.get("category")
            if not entry_id or not category:
                return {"error": "entry_id and category are required for categorize."}
            for e in entries:
                if e["id"] == entry_id:
                    e["category"] = category
                    self._save(entries)
                    return {"message": "Entry categorized.", "entry": e}
            return {"error": f"Entry {entry_id} not found."}

        return {"error": f"Unknown action: {action}"}

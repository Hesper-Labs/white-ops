"""Notes tool - manage text notes."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from agent.tools.base import BaseTool

STORAGE_PATH = "/tmp/whiteops_notes.json"


class NotesTool(BaseTool):
    name = "notes"
    description = (
        "Create, list, search, update, and delete text notes. "
        "Notes support tags and are stored persistently."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "list", "search", "update", "delete"],
                "description": "Action to perform.",
            },
            "note_id": {
                "type": "string",
                "description": "Note ID (for update/delete).",
            },
            "title": {
                "type": "string",
                "description": "Note title.",
            },
            "content": {
                "type": "string",
                "description": "Note content.",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tags for the note.",
            },
            "query": {
                "type": "string",
                "description": "Search query (searches title, content, tags).",
            },
        },
        "required": ["action"],
    }

    def _load(self) -> list[dict]:
        path = Path(STORAGE_PATH)
        if path.exists():
            return json.loads(path.read_text())
        return []

    def _save(self, notes: list[dict]) -> None:
        Path(STORAGE_PATH).write_text(json.dumps(notes, indent=2, ensure_ascii=False))

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]
        notes = self._load()

        if action == "create":
            title = kwargs.get("title", "Untitled")
            content = kwargs.get("content", "")
            tags = kwargs.get("tags", [])

            note = {
                "id": uuid4().hex[:8],
                "title": title,
                "content": content,
                "tags": tags,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
            notes.append(note)
            self._save(notes)
            return {"message": "Note created.", "note": note}

        elif action == "list":
            tag = kwargs.get("tags")
            if tag:
                tag_set = set(tag) if isinstance(tag, list) else {tag}
                notes = [n for n in notes if set(n.get("tags", [])) & tag_set]
            # Return summary view
            summaries = [
                {
                    "id": n["id"],
                    "title": n["title"],
                    "tags": n.get("tags", []),
                    "created_at": n["created_at"],
                    "preview": n["content"][:100] + "..." if len(n.get("content", "")) > 100 else n.get("content", ""),
                }
                for n in notes
            ]
            return {"notes": summaries, "count": len(summaries)}

        elif action == "search":
            query = kwargs.get("query", "").lower()
            if not query:
                return {"error": "query is required for search."}

            results = []
            for n in notes:
                searchable = f"{n.get('title', '')} {n.get('content', '')} {' '.join(n.get('tags', []))}".lower()
                if query in searchable:
                    results.append(n)
            return {"results": results, "count": len(results)}

        elif action == "update":
            note_id = kwargs.get("note_id")
            if not note_id:
                return {"error": "note_id is required."}
            for note in notes:
                if note["id"] == note_id:
                    if "title" in kwargs:
                        note["title"] = kwargs["title"]
                    if "content" in kwargs:
                        note["content"] = kwargs["content"]
                    if "tags" in kwargs:
                        note["tags"] = kwargs["tags"]
                    note["updated_at"] = datetime.now().isoformat()
                    self._save(notes)
                    return {"message": "Note updated.", "note": note}
            return {"error": f"Note {note_id} not found."}

        elif action == "delete":
            note_id = kwargs.get("note_id")
            if not note_id:
                return {"error": "note_id is required."}
            for i, note in enumerate(notes):
                if note["id"] == note_id:
                    removed = notes.pop(i)
                    self._save(notes)
                    return {"message": "Note deleted.", "note": removed}
            return {"error": f"Note {note_id} not found."}

        return {"error": f"Unknown action: {action}"}

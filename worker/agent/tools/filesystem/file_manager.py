"""File manager tool - create, read, copy, move, and organize files."""

import json
import os
import shutil
from pathlib import Path
from typing import Any

from agent.tools.base import BaseTool


class FileManagerTool(BaseTool):
    name = "file_manager"
    description = (
        "Manage files and directories. "
        "Supports: read, write, copy, move, delete, list, mkdir, "
        "compress (zip), and get file info."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["read", "write", "copy", "move", "delete", "list", "mkdir", "zip", "info"],
            },
            "path": {"type": "string", "description": "File or directory path"},
            "content": {"type": "string", "description": "Content to write"},
            "destination": {"type": "string", "description": "Destination path (for copy/move)"},
        },
        "required": ["action", "path"],
    }

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]
        path = kwargs["path"]

        if action == "read":
            with open(path) as f:
                content = f.read()
            return content[:20000]  # Limit for safety

        elif action == "write":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                f.write(kwargs.get("content", ""))
            return f"Written to: {path}"

        elif action == "copy":
            dest = kwargs.get("destination", "")
            shutil.copy2(path, dest)
            return f"Copied {path} to {dest}"

        elif action == "move":
            dest = kwargs.get("destination", "")
            shutil.move(path, dest)
            return f"Moved {path} to {dest}"

        elif action == "delete":
            p = Path(path)
            if p.is_dir():
                shutil.rmtree(path)
            else:
                p.unlink()
            return f"Deleted: {path}"

        elif action == "list":
            items = []
            for item in Path(path).iterdir():
                items.append({
                    "name": item.name,
                    "type": "dir" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else 0,
                })
            return json.dumps(sorted(items, key=lambda x: (x["type"], x["name"])))

        elif action == "mkdir":
            Path(path).mkdir(parents=True, exist_ok=True)
            return f"Created directory: {path}"

        elif action == "zip":
            dest = kwargs.get("destination", path + ".zip")
            shutil.make_archive(dest.replace(".zip", ""), "zip", path)
            return f"Compressed to: {dest}"

        elif action == "info":
            p = Path(path)
            stat = p.stat()
            return json.dumps({
                "name": p.name,
                "size": stat.st_size,
                "is_file": p.is_file(),
                "is_dir": p.is_dir(),
                "extension": p.suffix,
                "exists": p.exists(),
            })

        return f"Unknown action: {action}"

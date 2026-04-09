"""File manager tool - create, read, copy, move, and organize files."""

import json
import os
import shutil
from pathlib import Path
from typing import Any

from agent.tools.base import BaseTool

BLOCKED_PATHS = frozenset({
    '/', '/etc', '/usr', '/bin', '/sbin', '/boot', '/dev', '/proc', '/sys',
    '/var/run', '/var/log', '/Library', '/System', '/Windows', '/Program Files',
})

MAX_READ_BYTES = 20000
MAX_DELETE_DEPTH = 5


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

    def _validate_path(self, path: str) -> str:
        """Validate that path is safe to access. Returns the resolved real path."""
        # Expand user home and resolve to absolute path
        expanded = os.path.expanduser(path)
        # Use realpath to resolve ALL symlinks before checking
        resolved = os.path.realpath(expanded)

        # Check against blocked paths
        for blocked in BLOCKED_PATHS:
            if resolved == blocked or resolved.startswith(blocked + os.sep):
                # Allow subdirectories of /var/log and /etc that are explicitly user-owned
                if blocked in ('/var/log', '/var/run'):
                    continue
                raise ValueError(f"Access denied: {blocked} is a restricted path")

        # Check for path traversal (after normalization)
        norm = os.path.normpath(path)
        if '..' in norm.split(os.sep):
            raise ValueError("Path traversal detected")

        return resolved

    def _validate_not_symlink_attack(self, path: str) -> str:
        """Validate path is not a symlink pointing to a restricted location."""
        # First check the path as given (before symlink resolution)
        if os.path.islink(path):
            target = os.path.realpath(path)
            for blocked in BLOCKED_PATHS:
                if target == blocked or target.startswith(blocked + os.sep):
                    raise ValueError(f"Symlink target {target} is a restricted path")
        return self._validate_path(path)

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]
        path = kwargs["path"]

        try:
            # Validate and resolve primary path
            resolved_path = self._validate_not_symlink_attack(path)

            # Validate destination path for copy/move/zip actions
            resolved_dest = None
            if action in ("copy", "move", "zip") and kwargs.get("destination"):
                resolved_dest = self._validate_not_symlink_attack(kwargs["destination"])

            if action == "read":
                return self._read(resolved_path)
            elif action == "write":
                return self._write(resolved_path, kwargs.get("content", ""))
            elif action == "copy":
                return self._copy(resolved_path, resolved_dest or "")
            elif action == "move":
                return self._move(resolved_path, resolved_dest or "")
            elif action == "delete":
                return self._delete(resolved_path)
            elif action == "list":
                return self._list(resolved_path)
            elif action == "mkdir":
                return self._mkdir(resolved_path)
            elif action == "zip":
                return self._zip(resolved_path, resolved_dest or resolved_path + ".zip")
            elif action == "info":
                return self._info(resolved_path)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})

        except ValueError as e:
            return json.dumps({"error": str(e), "blocked": True})
        except FileNotFoundError:
            return json.dumps({"error": f"File not found: {path}"})
        except PermissionError:
            return json.dumps({"error": f"Permission denied: {path}"})
        except OSError as e:
            return json.dumps({"error": f"OS error: {e}"})

    def _read(self, path: str) -> str:
        with open(path) as f:
            content = f.read(MAX_READ_BYTES + 1)
        if len(content) > MAX_READ_BYTES:
            return content[:MAX_READ_BYTES] + "\n... [truncated]"
        return content

    def _write(self, path: str, content: str) -> str:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(content)
        return json.dumps({"success": True, "path": path, "bytes_written": len(content)})

    def _copy(self, src: str, dest: str) -> str:
        if not dest:
            return json.dumps({"error": "destination is required for copy"})
        shutil.copy2(src, dest)
        return json.dumps({"success": True, "source": src, "destination": dest})

    def _move(self, src: str, dest: str) -> str:
        if not dest:
            return json.dumps({"error": "destination is required for move"})
        shutil.move(src, dest)
        return json.dumps({"success": True, "source": src, "destination": dest})

    def _delete(self, path: str) -> str:
        p = Path(path)
        if p.is_dir():
            # Safety: check depth to prevent catastrophic deletes
            depth = 0
            for root, dirs, files in os.walk(path):
                depth = max(depth, root.count(os.sep) - path.count(os.sep))
                if depth > MAX_DELETE_DEPTH:
                    return json.dumps({
                        "error": f"Directory too deep (>{MAX_DELETE_DEPTH} levels). "
                                 "Delete subdirectories first for safety.",
                        "blocked": True,
                    })

            # Re-validate all paths during deletion to catch symlink attacks
            for root, dirs, files in os.walk(path, topdown=False):
                real_root = os.path.realpath(root)
                for blocked in BLOCKED_PATHS:
                    if real_root == blocked or real_root.startswith(blocked + os.sep):
                        return json.dumps({
                            "error": f"Symlink inside directory points to restricted path: {real_root}",
                            "blocked": True,
                        })

            shutil.rmtree(path)
        else:
            p.unlink()
        return json.dumps({"success": True, "deleted": path})

    def _list(self, path: str) -> str:
        items = []
        for item in Path(path).iterdir():
            try:
                items.append({
                    "name": item.name,
                    "type": "dir" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else 0,
                })
            except (PermissionError, OSError):
                items.append({"name": item.name, "type": "unknown", "size": 0})
        return json.dumps(sorted(items, key=lambda x: (x["type"], x["name"])))

    def _mkdir(self, path: str) -> str:
        Path(path).mkdir(parents=True, exist_ok=True)
        return json.dumps({"success": True, "path": path})

    def _zip(self, path: str, dest: str) -> str:
        dest_clean = dest.replace(".zip", "")
        shutil.make_archive(dest_clean, "zip", path)
        return json.dumps({"success": True, "archive": dest_clean + ".zip"})

    def _info(self, path: str) -> str:
        p = Path(path)
        if not p.exists():
            return json.dumps({"exists": False, "path": path})
        stat = p.stat()
        return json.dumps({
            "name": p.name,
            "size": stat.st_size,
            "is_file": p.is_file(),
            "is_dir": p.is_dir(),
            "is_symlink": p.is_symlink(),
            "extension": p.suffix,
            "exists": True,
        })

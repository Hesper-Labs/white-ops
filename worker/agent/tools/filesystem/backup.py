"""Backup tool - create and manage timestamped zip backups."""

import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from agent.tools.base import BaseTool

DEFAULT_BACKUP_DIR = "/tmp/whiteops_backups"


class BackupTool(BaseTool):
    name = "backup"
    description = (
        "Create timestamped zip backups of files and directories, "
        "list existing backups, and restore from backups."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create_backup", "list_backups", "restore"],
                "description": "Action to perform.",
            },
            "source_path": {
                "type": "string",
                "description": "Path to file or directory to back up.",
            },
            "backup_dir": {
                "type": "string",
                "description": f"Directory to store backups. Default: {DEFAULT_BACKUP_DIR}",
            },
            "backup_name": {
                "type": "string",
                "description": "Custom name prefix for the backup archive.",
            },
            "backup_file": {
                "type": "string",
                "description": "Path to backup zip file (for restore).",
            },
            "restore_path": {
                "type": "string",
                "description": "Path to restore files to (for restore).",
            },
        },
        "required": ["action"],
    }

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]
        backup_dir = kwargs.get("backup_dir", DEFAULT_BACKUP_DIR)
        Path(backup_dir).mkdir(parents=True, exist_ok=True)

        if action == "create_backup":
            source = kwargs.get("source_path")
            if not source:
                return {"error": "source_path is required."}

            source_path = Path(source)
            if not source_path.exists():
                return {"error": f"Source not found: {source}"}

            name_prefix = kwargs.get("backup_name", source_path.name)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_name = f"{name_prefix}_{timestamp}.zip"
            zip_path = Path(backup_dir) / zip_name

            try:
                file_count = 0
                total_size = 0
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    if source_path.is_file():
                        zf.write(source_path, source_path.name)
                        file_count = 1
                        total_size = source_path.stat().st_size
                    elif source_path.is_dir():
                        for file in source_path.rglob("*"):
                            if file.is_file():
                                arcname = file.relative_to(source_path.parent)
                                zf.write(file, arcname)
                                file_count += 1
                                total_size += file.stat().st_size

                backup_size = zip_path.stat().st_size
                return {
                    "message": "Backup created.",
                    "backup_file": str(zip_path),
                    "source": source,
                    "files_backed_up": file_count,
                    "original_size_bytes": total_size,
                    "backup_size_bytes": backup_size,
                    "compression_ratio": round(backup_size / total_size, 2) if total_size else 0,
                    "timestamp": timestamp,
                }
            except Exception as e:
                return {"error": f"Backup failed: {e}"}

        elif action == "list_backups":
            backups = []
            for f in sorted(Path(backup_dir).glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True):
                stat = f.stat()
                backups.append({
                    "name": f.name,
                    "path": str(f),
                    "size_bytes": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
            return {"backups": backups, "count": len(backups), "backup_dir": backup_dir}

        elif action == "restore":
            backup_file = kwargs.get("backup_file")
            restore_path = kwargs.get("restore_path")
            if not backup_file:
                return {"error": "backup_file is required."}
            if not restore_path:
                return {"error": "restore_path is required."}

            backup_path = Path(backup_file)
            if not backup_path.exists():
                return {"error": f"Backup file not found: {backup_file}"}

            try:
                restore_dir = Path(restore_path)
                restore_dir.mkdir(parents=True, exist_ok=True)

                with zipfile.ZipFile(backup_path, "r") as zf:
                    file_list = zf.namelist()
                    zf.extractall(restore_dir)

                return {
                    "message": "Backup restored.",
                    "backup_file": backup_file,
                    "restored_to": restore_path,
                    "files_restored": len(file_list),
                }
            except Exception as e:
                return {"error": f"Restore failed: {e}"}

        return {"error": f"Unknown action: {action}"}

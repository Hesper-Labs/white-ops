"""Backup tool - create and manage tar.gz archives with metadata."""

import json
import os
import shutil
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

MAX_OUTPUT_BYTES = 50 * 1024
MAX_BACKUP_SIZE = 1024 * 1024 * 1024  # 1GB
DEFAULT_BACKUP_DIR = "/tmp/whiteops_backups"


def _truncate(result: str) -> str:
    if len(result) > MAX_OUTPUT_BYTES:
        return result[:MAX_OUTPUT_BYTES] + "\n... [output truncated at 50KB]"
    return result


class BackupTool(BaseTool):
    name = "backup"
    description = (
        "Create and manage compressed tar.gz backups of files and directories. "
        "Supports creating backups with metadata, restoring from archives, "
        "listing existing backups, and viewing schedule info. Max backup size: 1GB."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create_backup", "restore_backup", "list_backups", "schedule_info"],
                "description": "Backup action to perform.",
            },
            "source_paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of file/directory paths to back up (for create_backup).",
            },
            "dest_path": {
                "type": "string",
                "description": "Destination directory for backup or restore.",
            },
            "compress": {
                "type": "boolean",
                "description": "Whether to compress the archive (default: true).",
            },
            "backup_path": {
                "type": "string",
                "description": "Path to backup archive (for restore_backup).",
            },
            "directory": {
                "type": "string",
                "description": "Directory to list backups from (for list_backups).",
            },
        },
        "required": ["action"],
    }

    def _calculate_total_size(self, paths: list[str]) -> int:
        """Calculate total size of all source paths."""
        total = 0
        for p in paths:
            path = Path(p)
            if path.is_file():
                total += path.stat().st_size
            elif path.is_dir():
                for f in path.rglob("*"):
                    if f.is_file():
                        total += f.stat().st_size
        return total

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action", "")
        logger.info("backup_execute", action=action)

        try:
            if action == "create_backup":
                return await self._create_backup(kwargs)
            elif action == "restore_backup":
                return await self._restore_backup(kwargs)
            elif action == "list_backups":
                return await self._list_backups(kwargs)
            elif action == "schedule_info":
                return await self._schedule_info()
            else:
                return _truncate(json.dumps({"error": f"Unknown action: {action}"}))
        except Exception as e:
            logger.error("backup_failed", action=action, error=str(e))
            return _truncate(json.dumps({"error": f"Backup operation failed: {e}"}))

    async def _create_backup(self, kwargs: dict) -> str:
        source_paths = kwargs.get("source_paths", [])
        dest_path = kwargs.get("dest_path", DEFAULT_BACKUP_DIR)
        compress = kwargs.get("compress", True)

        if not source_paths:
            return _truncate(json.dumps({"error": "'source_paths' list is required"}))

        # Validate all source paths exist
        missing = [p for p in source_paths if not Path(p).exists()]
        if missing:
            return _truncate(json.dumps({"error": f"Source paths not found: {missing}"}))

        # Check total size
        total_size = self._calculate_total_size(source_paths)
        if total_size > MAX_BACKUP_SIZE:
            return _truncate(json.dumps({
                "error": f"Total size ({total_size / (1024**3):.2f}GB) exceeds maximum backup size (1GB)",
            }))

        # Create destination directory
        Path(dest_path).mkdir(parents=True, exist_ok=True)

        # Generate backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = ".tar.gz" if compress else ".tar"
        backup_name = f"backup_{timestamp}{ext}"
        backup_file = str(Path(dest_path) / backup_name)

        # Create metadata
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "source_paths": source_paths,
            "total_original_size": total_size,
            "compressed": compress,
            "created_by": "whiteops_backup_tool",
        }

        # Write metadata to temp file
        metadata_file = Path(dest_path) / f".backup_meta_{timestamp}.json"
        metadata_file.write_text(json.dumps(metadata, indent=2))

        # Create archive
        mode = "w:gz" if compress else "w"
        file_count = 0

        try:
            with tarfile.open(backup_file, mode) as tar:
                # Add metadata
                tar.add(str(metadata_file), arcname=".backup_metadata.json")

                # Add source files
                for src in source_paths:
                    src_path = Path(src)
                    arcname = src_path.name
                    tar.add(src, arcname=arcname)
                    if src_path.is_file():
                        file_count += 1
                    elif src_path.is_dir():
                        file_count += sum(1 for f in src_path.rglob("*") if f.is_file())

            # Clean up metadata temp file
            metadata_file.unlink(missing_ok=True)

            backup_size = Path(backup_file).stat().st_size
            compression_ratio = round(backup_size / total_size, 3) if total_size > 0 else 0

            logger.info("backup_created", file=backup_file, files=file_count, size=backup_size)
            return _truncate(json.dumps({
                "success": True,
                "backup_file": backup_file,
                "source_paths": source_paths,
                "files_backed_up": file_count,
                "original_size_bytes": total_size,
                "backup_size_bytes": backup_size,
                "compression_ratio": compression_ratio,
                "timestamp": timestamp,
                "compressed": compress,
            }))
        except Exception as e:
            metadata_file.unlink(missing_ok=True)
            raise

    async def _restore_backup(self, kwargs: dict) -> str:
        backup_path = kwargs.get("backup_path", "")
        dest_path = kwargs.get("dest_path", "")

        if not backup_path:
            return _truncate(json.dumps({"error": "'backup_path' is required"}))
        if not dest_path:
            return _truncate(json.dumps({"error": "'dest_path' is required"}))

        if not Path(backup_path).exists():
            return _truncate(json.dumps({"error": f"Backup file not found: {backup_path}"}))

        Path(dest_path).mkdir(parents=True, exist_ok=True)

        try:
            mode = "r:gz" if backup_path.endswith(".gz") else "r"
            with tarfile.open(backup_path, mode) as tar:
                # Security: check for path traversal
                for member in tar.getmembers():
                    member_path = os.path.join(dest_path, member.name)
                    if not os.path.abspath(member_path).startswith(os.path.abspath(dest_path)):
                        return _truncate(json.dumps({
                            "error": "Backup contains unsafe paths (path traversal detected)",
                        }))

                file_list = tar.getnames()
                tar.extractall(dest_path, filter="data")

            # Read metadata if available
            metadata = {}
            meta_path = Path(dest_path) / ".backup_metadata.json"
            if meta_path.exists():
                metadata = json.loads(meta_path.read_text())

            logger.info("backup_restored", file=backup_path, dest=dest_path, files=len(file_list))
            return _truncate(json.dumps({
                "success": True,
                "backup_file": backup_path,
                "restored_to": dest_path,
                "files_restored": len(file_list),
                "original_metadata": metadata,
            }))
        except Exception as e:
            logger.error("backup_restore_failed", error=str(e))
            return _truncate(json.dumps({"error": f"Restore failed: {e}"}))

    async def _list_backups(self, kwargs: dict) -> str:
        directory = kwargs.get("directory", DEFAULT_BACKUP_DIR)

        if not Path(directory).exists():
            return _truncate(json.dumps({"backups": [], "count": 0, "directory": directory}))

        backups = []
        for f in sorted(Path(directory).glob("*.tar*"), key=lambda p: p.stat().st_mtime, reverse=True):
            stat = f.stat()
            backups.append({
                "name": f.name,
                "path": str(f),
                "size_bytes": stat.st_size,
                "size_human": f"{stat.st_size / (1024*1024):.2f}MB",
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "compressed": f.name.endswith(".gz"),
            })

        logger.info("backup_list", directory=directory, count=len(backups))
        return _truncate(json.dumps({
            "backups": backups,
            "count": len(backups),
            "directory": directory,
        }))

    async def _schedule_info(self) -> str:
        return _truncate(json.dumps({
            "message": "Backup scheduling is managed externally via cron or task scheduler.",
            "recommended_schedule": {
                "daily": "0 2 * * * (2:00 AM daily)",
                "weekly": "0 2 * * 0 (2:00 AM every Sunday)",
                "monthly": "0 2 1 * * (2:00 AM first day of month)",
            },
            "notes": [
                "Use system cron or task scheduler for automated backups.",
                "The create_backup action can be called programmatically on any schedule.",
                "Max backup size is 1GB per archive.",
                "Backups are stored as .tar.gz compressed archives with metadata.",
            ],
        }))

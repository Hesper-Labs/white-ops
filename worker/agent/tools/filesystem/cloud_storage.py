"""Cloud storage tool - upload, download, list, delete, and share files via MinIO."""

import json
import os
import time
from typing import Any

from agent.tools.base import BaseTool


class CloudStorageTool(BaseTool):
    name = "cloud_storage"
    description = (
        "Manage files in cloud storage (MinIO/S3-compatible). Upload, download, "
        "list, delete files, and generate shareable links."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["upload", "download", "list_files", "delete", "share_link"],
                "description": "The cloud storage action to perform",
            },
            "local_path": {
                "type": "string",
                "description": "Local file path for upload/download",
            },
            "remote_path": {
                "type": "string",
                "description": "Remote object key/path in the bucket",
            },
            "bucket": {
                "type": "string",
                "description": "Bucket name (overrides default)",
            },
            "prefix": {
                "type": "string",
                "description": "Prefix filter for list_files (folder path)",
            },
            "expires": {
                "type": "integer",
                "description": "Link expiration in seconds for share_link (default 3600)",
            },
            "recursive": {
                "type": "boolean",
                "description": "List files recursively (default false)",
            },
        },
        "required": ["action"],
    }

    def _get_client(self) -> Any:
        """Create a MinIO client from config settings."""
        try:
            from minio import Minio
        except ImportError:
            raise ImportError("minio package is required: pip install minio")

        from agent.config import settings

        return Minio(
            settings.minio_endpoint,
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=False,  # Typically local dev; set True for production
        )

    def _get_bucket(self, kwargs: dict) -> str:
        if kwargs.get("bucket"):
            return kwargs["bucket"]
        from agent.config import settings
        return settings.minio_bucket

    def _ensure_bucket(self, client: Any, bucket: str) -> None:
        """Create bucket if it doesn't exist."""
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]

        try:
            if action == "upload":
                return self._upload(kwargs)
            elif action == "download":
                return self._download(kwargs)
            elif action == "list_files":
                return self._list_files(kwargs)
            elif action == "delete":
                return self._delete(kwargs)
            elif action == "share_link":
                return self._share_link(kwargs)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except ImportError as e:
            return json.dumps({"error": str(e)})
        except Exception as e:
            return json.dumps({"error": f"Cloud storage operation failed: {e}"})

    def _upload(self, kwargs: dict) -> str:
        local_path = kwargs.get("local_path")
        remote_path = kwargs.get("remote_path")
        if not local_path or not remote_path:
            return json.dumps({"error": "local_path and remote_path are required"})

        if not os.path.isfile(local_path):
            return json.dumps({"error": f"File not found: {local_path}"})

        client = self._get_client()
        bucket = self._get_bucket(kwargs)
        self._ensure_bucket(client, bucket)

        file_size = os.path.getsize(local_path)

        # Guess content type
        import mimetypes
        content_type = mimetypes.guess_type(local_path)[0] or "application/octet-stream"

        result = client.fput_object(
            bucket, remote_path, local_path, content_type=content_type
        )

        return json.dumps({
            "success": True,
            "bucket": bucket,
            "remote_path": remote_path,
            "size": file_size,
            "etag": result.etag,
            "content_type": content_type,
        })

    def _download(self, kwargs: dict) -> str:
        remote_path = kwargs.get("remote_path")
        local_path = kwargs.get("local_path")
        if not remote_path or not local_path:
            return json.dumps({"error": "remote_path and local_path are required"})

        client = self._get_client()
        bucket = self._get_bucket(kwargs)

        # Ensure download directory exists
        os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)

        client.fget_object(bucket, remote_path, local_path)

        file_size = os.path.getsize(local_path)
        return json.dumps({
            "success": True,
            "bucket": bucket,
            "remote_path": remote_path,
            "local_path": local_path,
            "size": file_size,
        })

    def _list_files(self, kwargs: dict) -> str:
        client = self._get_client()
        bucket = self._get_bucket(kwargs)
        prefix = kwargs.get("prefix", "")
        recursive = kwargs.get("recursive", False)

        objects = client.list_objects(bucket, prefix=prefix, recursive=recursive)

        files = []
        for obj in objects:
            files.append({
                "name": obj.object_name,
                "size": obj.size,
                "last_modified": obj.last_modified.isoformat() if obj.last_modified else "",
                "is_dir": obj.is_dir,
                "etag": obj.etag or "",
            })
            if len(files) >= 500:
                break

        return json.dumps({
            "bucket": bucket,
            "prefix": prefix,
            "files": files,
            "count": len(files),
            "truncated": len(files) >= 500,
        })

    def _delete(self, kwargs: dict) -> str:
        remote_path = kwargs.get("remote_path")
        if not remote_path:
            return json.dumps({"error": "remote_path is required"})

        client = self._get_client()
        bucket = self._get_bucket(kwargs)

        # Verify object exists
        try:
            client.stat_object(bucket, remote_path)
        except Exception:
            return json.dumps({"error": f"Object not found: {remote_path}"})

        client.remove_object(bucket, remote_path)

        return json.dumps({
            "success": True,
            "bucket": bucket,
            "remote_path": remote_path,
            "deleted": True,
        })

    def _share_link(self, kwargs: dict) -> str:
        remote_path = kwargs.get("remote_path")
        if not remote_path:
            return json.dumps({"error": "remote_path is required"})

        client = self._get_client()
        bucket = self._get_bucket(kwargs)
        expires = kwargs.get("expires", 3600)

        from datetime import timedelta

        url = client.presigned_get_object(
            bucket, remote_path, expires=timedelta(seconds=expires)
        )

        return json.dumps({
            "success": True,
            "bucket": bucket,
            "remote_path": remote_path,
            "url": url,
            "expires_in_seconds": expires,
        })

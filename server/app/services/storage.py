"""MinIO file storage service."""

import io
import uuid
from pathlib import Path

import structlog
from minio import Minio
from minio.error import S3Error

from app.config import settings

logger = structlog.get_logger()


class StorageService:
    def __init__(self) -> None:
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=False,
        )
        self.bucket = settings.minio_bucket
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info("bucket_created", bucket=self.bucket)
        except S3Error as e:
            logger.error("bucket_check_failed", error=str(e))

    def upload(
        self,
        content: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        prefix: str = "uploads",
    ) -> str:
        """Upload a file and return the storage path (object key)."""
        ext = Path(filename).suffix
        object_name = f"{prefix}/{uuid.uuid4()}{ext}"

        self.client.put_object(
            self.bucket,
            object_name,
            io.BytesIO(content),
            length=len(content),
            content_type=content_type,
        )

        logger.info("file_uploaded", path=object_name, size=len(content))
        return object_name

    def download(self, object_name: str) -> bytes:
        """Download a file and return its content."""
        response = self.client.get_object(self.bucket, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def get_presigned_url(self, object_name: str, expires_hours: int = 1) -> str:
        """Generate a presigned download URL."""
        from datetime import timedelta

        return self.client.presigned_get_object(
            self.bucket, object_name, expires=timedelta(hours=expires_hours)
        )

    def delete(self, object_name: str) -> None:
        """Delete a file."""
        self.client.remove_object(self.bucket, object_name)
        logger.info("file_deleted", path=object_name)

    def list_files(self, prefix: str = "") -> list[dict]:
        """List files with a prefix."""
        objects = self.client.list_objects(self.bucket, prefix=prefix, recursive=True)
        return [
            {
                "name": obj.object_name,
                "size": obj.size,
                "last_modified": str(obj.last_modified),
            }
            for obj in objects
        ]


# Singleton
storage = StorageService()

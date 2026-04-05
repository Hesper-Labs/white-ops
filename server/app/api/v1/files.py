"""File management API with MinIO storage."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.file import File
from app.models.user import User

router = APIRouter()


def _get_storage():
    from app.services.storage import storage
    return storage


@router.get("/")
async def list_files(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    task_id: str | None = None,
    limit: int = 50,
) -> list[dict]:
    query = select(File)
    if task_id:
        query = query.where(File.task_id == uuid.UUID(task_id))
    result = await db.execute(query.order_by(File.created_at.desc()).limit(limit))
    files = result.scalars().all()
    return [
        {
            "id": str(f.id),
            "filename": f.original_filename,
            "content_type": f.content_type,
            "size_bytes": f.size_bytes,
            "task_id": str(f.task_id) if f.task_id else None,
            "tags": f.tags,
            "created_at": str(f.created_at),
        }
        for f in files
    ]


@router.post("/upload")
async def upload_file(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    task_id: str | None = None,
) -> dict:
    content = await file.read()
    filename = file.filename or "unknown"
    content_type = file.content_type or "application/octet-stream"

    # Upload to MinIO
    storage = _get_storage()
    storage_path = storage.upload(content, filename, content_type)

    db_file = File(
        filename=filename,
        original_filename=filename,
        content_type=content_type,
        size_bytes=len(content),
        storage_path=storage_path,
        bucket=storage.bucket,
        uploaded_by_user_id=user.id,
    )
    if task_id:
        db_file.task_id = uuid.UUID(task_id)
    db.add(db_file)
    await db.flush()
    await db.refresh(db_file)
    return {
        "id": str(db_file.id),
        "filename": db_file.original_filename,
        "size": db_file.size_bytes,
    }


@router.get("/{file_id}")
async def get_file_metadata(
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    result = await db.execute(select(File).where(File.id == file_id))
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    return {
        "id": str(f.id),
        "filename": f.original_filename,
        "content_type": f.content_type,
        "size_bytes": f.size_bytes,
        "tags": f.tags,
        "metadata": f.metadata_,
        "created_at": str(f.created_at),
    }


@router.get("/{file_id}/download")
async def download_file(
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    result = await db.execute(select(File).where(File.id == file_id))
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")

    storage = _get_storage()
    content = storage.download(f.storage_path)

    import io
    return StreamingResponse(
        io.BytesIO(content),
        media_type=f.content_type,
        headers={"Content-Disposition": f'attachment; filename="{f.original_filename}"'},
    )


@router.get("/{file_id}/url")
async def get_download_url(
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    result = await db.execute(select(File).where(File.id == file_id))
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")

    storage = _get_storage()
    url = storage.get_presigned_url(f.storage_path)
    return {"url": url, "filename": f.original_filename, "expires_in": 3600}


@router.delete("/{file_id}", status_code=204)
async def delete_file(
    file_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    result = await db.execute(select(File).where(File.id == file_id))
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")

    storage = _get_storage()
    storage.delete(f.storage_path)
    await db.delete(f)

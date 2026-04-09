import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.code_review import CodeReview
from app.models.user import User

router = APIRouter()


class CodeReviewCreate(BaseModel):
    title: str
    task_id: str | None = None
    agent_id: str | None = None
    files_changed: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    diff_data: dict = {}


class CodeReviewComment(BaseModel):
    content: str
    file_path: str | None = None
    line_number: int | None = None


class CodeReviewReject(BaseModel):
    reason: str


@router.get("/")
async def list_code_reviews(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_filter: str | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    query = select(CodeReview).where(CodeReview.is_deleted.is_(False))
    if status_filter:
        query = query.where(CodeReview.status == status_filter)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    result = await db.execute(
        query.order_by(CodeReview.created_at.desc()).offset(skip).limit(limit)
    )
    reviews = result.scalars().all()
    return {
        "items": [
            {
                "id": str(r.id),
                "title": r.title,
                "task_id": str(r.task_id) if r.task_id else None,
                "agent_id": str(r.agent_id) if r.agent_id else None,
                "status": r.status,
                "files_changed": r.files_changed,
                "lines_added": r.lines_added,
                "lines_removed": r.lines_removed,
                "diff_data": r.diff_data,
                "reviewer_id": str(r.reviewer_id) if r.reviewer_id else None,
                "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
                "review_comment": r.review_comment,
                "comments": r.comments,
                "created_at": r.created_at.isoformat(),
            }
            for r in reviews
        ],
        "total": total,
    }


@router.get("/{review_id}")
async def get_code_review(
    review_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    result = await db.execute(
        select(CodeReview).where(
            CodeReview.id == uuid.UUID(review_id),
            CodeReview.is_deleted.is_(False),
        )
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Code review not found")
    return {
        "id": str(review.id),
        "title": review.title,
        "task_id": str(review.task_id) if review.task_id else None,
        "agent_id": str(review.agent_id) if review.agent_id else None,
        "status": review.status,
        "files_changed": review.files_changed,
        "lines_added": review.lines_added,
        "lines_removed": review.lines_removed,
        "diff_data": review.diff_data,
        "reviewer_id": str(review.reviewer_id) if review.reviewer_id else None,
        "reviewed_at": review.reviewed_at.isoformat() if review.reviewed_at else None,
        "review_comment": review.review_comment,
        "comments": review.comments,
        "created_at": review.created_at.isoformat(),
    }


@router.post("/")
async def create_code_review(
    data: CodeReviewCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    review = CodeReview(
        title=data.title,
        task_id=uuid.UUID(data.task_id) if data.task_id else None,
        agent_id=uuid.UUID(data.agent_id) if data.agent_id else None,
        files_changed=data.files_changed,
        lines_added=data.lines_added,
        lines_removed=data.lines_removed,
        diff_data=data.diff_data,
        status="pending",
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return {"id": str(review.id), "status": "created"}


@router.post("/{review_id}/approve")
async def approve_code_review(
    review_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    result = await db.execute(
        select(CodeReview).where(
            CodeReview.id == uuid.UUID(review_id),
            CodeReview.is_deleted.is_(False),
        )
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Code review not found")

    review.status = "approved"
    review.reviewer_id = user.id
    review.reviewed_at = datetime.now(UTC)
    await db.commit()
    return {"id": str(review.id), "status": "approved"}


@router.post("/{review_id}/reject")
async def reject_code_review(
    review_id: str,
    data: CodeReviewReject,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    result = await db.execute(
        select(CodeReview).where(
            CodeReview.id == uuid.UUID(review_id),
            CodeReview.is_deleted.is_(False),
        )
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Code review not found")

    review.status = "rejected"
    review.reviewer_id = user.id
    review.reviewed_at = datetime.now(UTC)
    review.review_comment = data.reason
    await db.commit()
    return {"id": str(review.id), "status": "rejected"}


@router.post("/{review_id}/comments")
async def add_comment(
    review_id: str,
    data: CodeReviewComment,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    result = await db.execute(
        select(CodeReview).where(
            CodeReview.id == uuid.UUID(review_id),
            CodeReview.is_deleted.is_(False),
        )
    )
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=404, detail="Code review not found")

    comments = list(review.comments or [])
    comments.append({
        "id": str(uuid.uuid4()),
        "user_id": str(user.id),
        "user_name": user.full_name,
        "content": data.content,
        "file_path": data.file_path,
        "line_number": data.line_number,
        "created_at": datetime.now(UTC).isoformat(),
    })
    review.comments = comments
    await db.commit()
    return {"id": str(review.id), "comment_count": len(comments)}

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_operator
from app.db.session import get_db
from app.models.user import User
from app.models.workflow import Workflow, WorkflowStep

router = APIRouter()


class WorkflowCreate(BaseModel):
    name: str
    description: str | None = None
    is_template: bool = False
    config: dict = {}


class WorkflowStepCreate(BaseModel):
    name: str
    step_type: str = "task"
    order: int = 0
    config: dict = {}
    agent_id: str | None = None
    depends_on: list[str] = []


@router.get("/")
async def list_workflows(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    count_result = await db.execute(select(func.count()).select_from(Workflow))
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Workflow).order_by(Workflow.created_at.desc()).offset(skip).limit(limit)
    )
    workflows = result.scalars().all()
    return {
        "items": [
            {
                "id": str(w.id),
                "name": w.name,
                "description": w.description,
                "status": w.status,
                "is_template": w.is_template,
                "created_at": str(w.created_at),
            }
            for w in workflows
        ],
        "total": total,
    }


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_workflow(
    data: WorkflowCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> dict:
    workflow = Workflow(
        name=data.name,
        description=data.description,
        is_template=data.is_template,
        config=data.config,
        created_by=user.id,
    )
    db.add(workflow)
    await db.flush()
    await db.refresh(workflow)
    return {"id": str(workflow.id), "name": workflow.name, "status": workflow.status}


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    steps_result = await db.execute(
        select(WorkflowStep)
        .where(WorkflowStep.workflow_id == workflow_id)
        .order_by(WorkflowStep.order)
    )
    steps = steps_result.scalars().all()

    return {
        "id": str(workflow.id),
        "name": workflow.name,
        "description": workflow.description,
        "status": workflow.status,
        "is_template": workflow.is_template,
        "config": workflow.config,
        "steps": [
            {
                "id": str(s.id),
                "name": s.name,
                "step_type": s.step_type,
                "order": s.order,
                "config": s.config,
                "agent_id": str(s.agent_id) if s.agent_id else None,
                "depends_on": s.depends_on,
                "status": s.status,
            }
            for s in steps
        ],
        "created_at": str(workflow.created_at),
    }


@router.post("/{workflow_id}/steps", status_code=status.HTTP_201_CREATED)
async def add_step(
    workflow_id: uuid.UUID,
    data: WorkflowStepCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> dict:
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Workflow not found")

    step = WorkflowStep(
        workflow_id=workflow_id,
        name=data.name,
        step_type=data.step_type,
        order=data.order,
        config=data.config,
        depends_on=data.depends_on,
    )
    if data.agent_id:
        step.agent_id = uuid.UUID(data.agent_id)
    db.add(step)
    await db.flush()
    await db.refresh(step)
    return {"id": str(step.id), "name": step.name, "order": step.order}


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> None:
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    await db.delete(workflow)

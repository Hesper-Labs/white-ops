from pydantic import BaseModel


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    instructions: str | None = None
    priority: str = "medium"
    agent_id: str | None = None
    deadline: str | None = None
    required_tools: list[str] = []
    max_retries: int = 3


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    instructions: str | None = None
    priority: str | None = None
    status: str | None = None
    agent_id: str | None = None
    deadline: str | None = None


class TaskResponse(BaseModel):
    id: str
    title: str
    description: str | None
    instructions: str | None
    status: str
    priority: str
    agent_id: str | None
    assigned_by: str | None
    result: str | None
    error: str | None
    output_files: list
    deadline: str | None
    started_at: str | None
    completed_at: str | None
    retry_count: int
    max_retries: int
    required_tools: list
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}

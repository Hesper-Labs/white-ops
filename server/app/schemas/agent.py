from pydantic import BaseModel


class AgentCreate(BaseModel):
    name: str
    description: str | None = None
    role: str = "general"
    llm_provider: str = "anthropic"
    llm_model: str = "claude-sonnet-4-20250514"
    system_prompt: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096
    enabled_tools: dict = {}
    max_concurrent_tasks: int = 3
    worker_id: str | None = None


class AgentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    role: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    system_prompt: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    enabled_tools: dict | None = None
    is_active: bool | None = None
    max_concurrent_tasks: int | None = None
    worker_id: str | None = None


class AgentResponse(BaseModel):
    id: str
    name: str
    description: str | None
    role: str
    status: str
    is_active: bool
    llm_provider: str
    llm_model: str
    system_prompt: str | None
    temperature: float
    max_tokens: int
    enabled_tools: dict
    max_concurrent_tasks: int
    tasks_completed: int
    tasks_failed: int
    email: str | None
    worker_id: str | None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}

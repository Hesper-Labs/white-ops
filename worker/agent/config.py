from pydantic_settings import BaseSettings


class WorkerSettings(BaseSettings):
    worker_name: str = "worker-01"
    worker_max_agents: int = 5
    master_url: str = "http://localhost:8000"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_root_user: str = "whiteops"
    minio_root_password: str = ""
    minio_bucket: str = "whiteops-files"

    # LLM
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    default_llm_provider: str = "anthropic"
    default_llm_model: str = "claude-sonnet-4-20250514"

    # Mail
    mail_server_host: str = "localhost"
    mail_server_port: int = 8025
    mail_domain: str = "whiteops.local"

    # Heartbeat
    heartbeat_interval: int = 30

    @property
    def redis_url(self) -> str:
        return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"

    model_config = {"env_prefix": "", "case_sensitive": False}

    def validate_required(self) -> list[str]:
        """Return list of configuration warnings."""
        warnings = []
        if not self.redis_password:
            warnings.append("REDIS_PASSWORD is not set - Redis connection may fail")
        if not self.minio_root_password:
            warnings.append("MINIO_ROOT_PASSWORD is not set - MinIO connection may fail")
        if not any([self.anthropic_api_key, self.openai_api_key, self.google_api_key]):
            warnings.append("No LLM API key configured - agent will not be able to process tasks")
        return warnings


settings = WorkerSettings()

# Log warnings at import time
_warnings = settings.validate_required()
if _warnings:
    import structlog
    _logger = structlog.get_logger()
    for w in _warnings:
        _logger.warning("config_warning", message=w)

"""Application configuration with startup validation and environment variable support."""

import sys
import warnings

from pydantic import model_validator
from pydantic_settings import BaseSettings

_INSECURE_DEFAULTS = {"change-me", "changeme", "password", "secret", "admin", "test"}


class Settings(BaseSettings):
    # ---- General ----
    app_name: str = "White-Ops"
    app_env: str = "production"  # production, staging, development, test
    debug: bool = False
    secret_key: str = "change-me"

    # ---- Database ----
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "whiteops"
    postgres_user: str = "whiteops"
    postgres_password: str = ""

    # ---- Redis ----
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""

    # ---- MinIO ----
    minio_endpoint: str = "localhost:9000"
    minio_root_user: str = "whiteops"
    minio_root_password: str = ""
    minio_bucket: str = "whiteops-files"
    minio_use_ssl: bool = False

    # ---- Auth / JWT ----
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    admin_email: str = "admin@whiteops.local"
    admin_password: str = ""

    # ---- Security ----
    password_min_length: int = 12
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    mfa_enabled: bool = False
    allowed_ips: str = ""
    request_body_max_size_mb: int = 10

    # ---- Rate Limiting ----
    rate_limit_per_ip: int = 120
    rate_limit_per_user: int = 300
    rate_limit_window_seconds: int = 60

    # ---- Vault ----
    vault_master_key: str = ""

    # ---- Mail ----
    mail_server_host: str = "localhost"
    mail_server_port: int = 8025
    mail_domain: str = "whiteops.local"

    # ---- External SMTP ----
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True

    # ---- CORS ----
    cors_origins: str = "http://localhost:3000"

    # ---- Integrations ----
    slack_webhook_url: str = ""
    telegram_bot_token: str = ""

    # ---- Cost Management ----
    monthly_budget_usd: float = 0.0
    budget_alert_thresholds: str = "80,90,100"

    # ---- Feature Flags ----
    feature_mfa: bool = True
    feature_webhooks: bool = True
    feature_cost_tracking: bool = True
    feature_circuit_breakers: bool = True
    feature_agent_memory: bool = True
    feature_triggers: bool = True

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """Fail fast in production if secrets are insecure defaults."""
        if self.app_env in ("production", "staging"):
            errors: list[str] = []

            if self.secret_key.lower() in _INSECURE_DEFAULTS or len(self.secret_key) < 32:
                errors.append("SECRET_KEY must be >=32 chars and not a default value")

            if self.jwt_secret_key.lower() in _INSECURE_DEFAULTS or len(self.jwt_secret_key) < 32:
                errors.append("JWT_SECRET_KEY must be >=32 chars and not a default value")

            if not self.postgres_password or self.postgres_password.lower() in _INSECURE_DEFAULTS:
                errors.append("POSTGRES_PASSWORD must be set and not a default value")

            if not self.admin_password or self.admin_password.lower() in _INSECURE_DEFAULTS:
                errors.append("ADMIN_PASSWORD must be set and not a default value")

            if self.jwt_secret_key == self.secret_key:
                errors.append("JWT_SECRET_KEY and SECRET_KEY must be different")

            if not self.vault_master_key or len(self.vault_master_key) < 32:
                errors.append("VAULT_MASTER_KEY must be set (>=32 chars) for secrets encryption")

            if not self.redis_password or self.redis_password.lower() in _INSECURE_DEFAULTS:
                errors.append("REDIS_PASSWORD must be set and not a default value")

            if self.cors_origins in ("http://localhost:3000", "http://localhost"):
                errors.append("CORS_ORIGINS must be set to production domain(s)")

            if errors:
                msg = "SECURITY CONFIGURATION ERRORS:\n" + "\n".join(f"  - {e}" for e in errors)
                print(f"\n{'='*60}\n{msg}\n{'='*60}\n", file=sys.stderr)
                raise ValueError(msg)

        elif self.app_env == "development":
            insecure = []
            if self.secret_key.lower() in _INSECURE_DEFAULTS:
                insecure.append("SECRET_KEY")
            if self.jwt_secret_key.lower() in _INSECURE_DEFAULTS:
                insecure.append("JWT_SECRET_KEY")
            if insecure:
                warnings.warn(
                    f"Insecure defaults for: {', '.join(insecure)}. "
                    "Set proper values before deploying to production.",
                    stacklevel=2,
                )

        return self

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    @property
    def is_production(self) -> bool:
        return self.app_env in ("production", "staging")

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()

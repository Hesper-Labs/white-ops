from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "White-Ops"
    app_env: str = "production"
    debug: bool = False
    secret_key: str = "change-me"

    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "whiteops"
    postgres_user: str = "whiteops"
    postgres_password: str = "changeme"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = "changeme"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_root_user: str = "whiteops"
    minio_root_password: str = "changeme"
    minio_bucket: str = "whiteops-files"

    # Auth
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440
    admin_email: str = "admin@whiteops.local"
    admin_password: str = "changeme"

    # Mail
    mail_server_host: str = "localhost"
    mail_server_port: int = 8025
    mail_domain: str = "whiteops.local"

    # CORS
    cors_origins: str = "http://localhost:3000"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()

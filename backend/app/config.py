from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://nova2:nova2secret@localhost:5432/nova2"
    DATABASE_URL_SYNC: str = "postgresql://nova2:nova2secret@localhost:5432/nova2"

    # Security
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Vault
    VAULT_ADDR: str = "http://localhost:8200"
    VAULT_TOKEN: str = "nova2-vault-token"
    VAULT_MOUNT_POINT: str = "nova2"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "nova2admin"
    MINIO_SECRET_KEY: str = "nova2secret"
    MINIO_BUCKET: str = "nova2-agents"
    MINIO_STORAGE_BUCKET: str = "nova2-storage"
    MINIO_SECURE: bool = False

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # N8N
    N8N_BASE_URL: str = "http://localhost:5678"
    N8N_BASIC_AUTH_USER: str = "nova2"
    N8N_BASIC_AUTH_PASSWORD: str = "nova2secret"

    # Admin
    ADMIN_EMAIL: str = "admin@nova2.local"
    ADMIN_PASSWORD: str = "Admin123!"

    # App
    APP_VERSION: str = "1.0.0"
    APP_NAME: str = "NOVA2 - AI Agentic Platform"

    # CORS — comma-separated origins, e.g. "http://localhost:3000,https://app.nova2.io"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()

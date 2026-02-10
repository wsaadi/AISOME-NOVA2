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
    MINIO_SECURE: bool = False

    # Admin
    ADMIN_EMAIL: str = "admin@nova2.local"
    ADMIN_PASSWORD: str = "Admin123!"

    # App
    APP_VERSION: str = "1.0.0"
    APP_NAME: str = "NOVA2 - AI Agentic Platform"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()

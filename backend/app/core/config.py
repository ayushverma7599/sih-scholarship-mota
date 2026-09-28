"""Application configuration.

All settings are environment-driven so the same code runs against SQLite
(zero-setup local dev) or PostgreSQL (docker-compose / production).
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Core ---
    APP_NAME: str = "UNNATI — Scholarship & Fellowship Management System"
    ENV: str = "development"
    API_PREFIX: str = "/api"

    # --- Database ---
    # SQLite fallback keeps the app runnable with no external services.
    DATABASE_URL: str = "sqlite:///./scholarship.db"

    # --- Auth ---
    JWT_SECRET: str = "dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12

    # --- PII encryption (Fernet). Dev key only; use KMS in production. ---
    # 32-url-safe-base64 bytes. Generated once for dev; override via env.
    FERNET_KEY: str = "DIFF9uhlgzh2qvkCBEFMx6GpkoznIKgnTaQFDSt7dyk="

    # --- File storage ---
    STORAGE_BACKEND: str = "local"  # local | s3 (s3 is a stub)
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_MB: int = 10
    ALLOWED_UPLOAD_TYPES: str = "application/pdf,image/png,image/jpeg,image/jpg"

    # --- AI / OCR ---
    USE_LLM_EXTRACTION: bool = False  # optional Claude extraction layer, off by default
    ANTHROPIC_API_KEY: str = ""

    # --- CORS ---
    FRONTEND_ORIGIN: str = "http://localhost:3000"

    @property
    def allowed_upload_types(self) -> list[str]:
        return [t.strip() for t in self.ALLOWED_UPLOAD_TYPES.split(",") if t.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

import os
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import RedisDsn, Field, model_validator
import logging

logger = logging.getLogger("app.core.config")


class AppSettings(BaseSettings):
    APP_NAME: str = "CogniDocent"
    LOGO_URL: str = Field(
        default="https://files.catbox.moe/00z6ji.png",
        validation_alias="LOGO_URL",
    )
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = (
        "CogniDocent is a powerful document search and retrieval tool that uses "
        "Large Language Models (LLMs) to provide accurate and relevant information "
        "from your documents."
    )
    APP_ROOT_PATH: str = "/api"
    APP_DOCS_PATH: str = "/"

    APP_ENV: str = Field(default="production", validation_alias="APP_ENV")
    APP_LOG_LEVEL: int = Field(default=logging.INFO, validation_alias="APP_LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Good practice: ignores extra env vars unrelated to this class
        frozen=True,
    )


class RedisSettings(BaseSettings):
    redis_url: RedisDsn = Field(alias="REDIS_URL")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", frozen=True
    )


class DatabaseSettings(BaseSettings):
    POSTGRES_USER: str = Field(validation_alias="DB_USER", default="postgres")
    POSTGRES_PASSWORD: str = Field(validation_alias="DB_PASSWORD", default="postgres")
    POSTGRES_HOST: str = Field(validation_alias="DB_HOST", default="postgres")
    POSTGRES_PORT: int = Field(validation_alias="DB_PORT", default=5432)
    POSTGRES_DB: str = Field(validation_alias="DB_NAME", default="postgres")
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/cognidocent",
        validation_alias="DATABASE_URL",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )


class CelerySettings(BaseSettings):
    # --- Broker & Backend ---
    broker_url: str = "amqp://guest:guest@localhost:5672//"
    result_backend: str | None = None

    # --- Serialization (Crucial for DTOs) ---
    task_serializer: str = "json"
    result_serializer: str = "json"
    accept_content: List[str] = ["json"]

    # --- Timezone Settings ---
    timezone: str = "UTC"
    enable_utc: bool = True

    # Result settings
    result_expires: int = 3600  # Results expire after 1 hour

    # Don't acknowledge the message until the task FINISHES.
    # If the Data Service crashes mid-extraction, RabbitMQ gives the task to someone else.
    task_acks_late: bool = True

    # Prevent a worker from grabbing 10 PDFs at once and crashing its RAM.
    # Tells the worker: "Only take 1 task at a time."
    worker_prefetch_multiplier: int = 1

    task_default_queue: str = "backend_queue"

    # Timeouts (Prevent hung GPU processes)
    # Hard kill after 30 minutes
    task_time_limit: int = 1800
    # Send a SoftTimeLimitExceeded exception at 29 minutes to allow graceful cleanup
    task_soft_time_limit: int = 1740

    @model_validator(mode="after")
    def assemble_settings(self):
        # Fallback for result_backend if it's not set explicitly but REDIS_URL is available
        redis_url = os.getenv("REDIS_URL")
        if redis_url and not self.result_backend:
            self.result_backend = redis_url
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CELERY_",  # Looks for CELERY_BROKER_URL in your .env
        case_sensitive=False,
        extra="ignore",
    )


class MinioSettings(BaseSettings):
    ENDPOINT: str = Field(validation_alias="MINIO_ENDPOINT")
    EXTERNAL_ENDPOINT: str = Field(
        validation_alias="MINIO_EXTERNAL_ENDPOINT", default="localhost:9000"
    )
    ACCESS_KEY: str = Field(validation_alias="MINIO_ACCESS_KEY")
    SECRET_KEY: str = Field(validation_alias="MINIO_SECRET_KEY")
    REGION: str = Field(validation_alias="MINIO_REGION", default="us-east-1")

    # Standardized Buckets
    INCOMING_UPLOADS_BUCKET: str = Field(
        validation_alias="MINIO_INCOMING_UPLOADS_BUCKET",
        default="uploads",
    )
    QUARANTINE_BUCKET: str = Field(
        validation_alias="MINIO_QUARANTINE_BUCKET",
        default="quarantine",
    )
    TRUSTED_BUCKET: str = Field(
        validation_alias="MINIO_TRUSTED_BUCKET", default="trusted"
    )
    INFECTED_BUCKET: str = Field(
        validation_alias="MINIO_INFECTED_BUCKET", default="infected"
    )
    THUMBNAILS_BUCKET: str = Field(
        validation_alias="MINIO_THUMBNAILS_BUCKET",
        default="thumbnails",
    )

    SECURE: bool = Field(validation_alias="MINIO_SECURE", default=False)

    AUTH_TOKEN: str | None = Field(validation_alias="MINIO_AUTH_TOKEN", default=None)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )


class AISettings(BaseSettings):
    DEFAULT_EMBEDDING_MODEL: str = Field(
        default="nomic-embed-text-v2-moe",
        validation_alias="DEFAULT_EMBEDDING_MODEL",
    )
    DEFAULT_EMBEDDING_PROVIDER: str = Field(
        default="ollama",
        validation_alias="DEFAULT_EMBEDDING_PROVIDER",
    )
    DEFAULT_EMBEDDING_DIMENSIONS: int = Field(
        default=768,
        validation_alias="DEFAULT_EMBEDDING_DIMENSIONS",
    )
    OLLAMA_BASE_URL: str = Field(
        default="http://localhost:11434",
        validation_alias="OLLAMA_BASE_URL",
    )
    DEFAULT_CHAT_MODEL: str = Field(
        default="gpt-4o-mini",
        validation_alias="DEFAULT_CHAT_MODEL",
    )
    DEFAULT_VISION_MODEL: str = Field(
        default="gpt-4o",
        validation_alias="DEFAULT_VISION_MODEL",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )


@lru_cache
def get_app_settings() -> AppSettings:
    return AppSettings()


@lru_cache
def get_db_settings() -> DatabaseSettings:
    return DatabaseSettings()


@lru_cache()
def get_redis_settings() -> RedisSettings:
    return RedisSettings()


@lru_cache()
def get_celery_settings() -> CelerySettings:
    return CelerySettings()


@lru_cache()
def get_minio_settings() -> MinioSettings:
    return MinioSettings()


@lru_cache()
def get_ai_settings() -> AISettings:
    return AISettings()

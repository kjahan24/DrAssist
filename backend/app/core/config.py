"""Centralized application configuration.

All runtime configuration is declared here as typed, validated settings
objects. Nothing outside this module should read `os.environ` directly —
import `get_settings()` instead so configuration stays a single source of
truth and remains easily testable (override via env vars or `.env`).
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "staging", "production", "test"]
LogFormat = Literal["json", "console"]


class _EnvBaseSettings(BaseSettings):
    """Common `.env` loading config, shared by every settings group.

    Each nested settings class below is instantiated independently via its
    own `default_factory` rather than receiving values from the parent
    `Settings` instance. Without this shared base, only the outer
    `Settings` object would read `.env` — the nested ones would see real
    process environment variables only, which breaks any process (e.g. a
    locally-run `uvicorn`) that isn't launched with `.env` already
    exported into the shell.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class BackendSettings(_EnvBaseSettings):
    host: str = Field(default="0.0.0.0", alias="BACKEND_HOST")
    port: int = Field(default=8000, alias="BACKEND_PORT")
    reload: bool = Field(default=False, alias="BACKEND_RELOAD")
    workers: int = Field(default=4, alias="BACKEND_WORKERS")
    secret_key: str = Field(alias="BACKEND_SECRET_KEY")
    allowed_hosts: str = Field(default="localhost,127.0.0.1", alias="BACKEND_ALLOWED_HOSTS")
    cors_origins: str = Field(default="http://localhost:3000", alias="BACKEND_CORS_ORIGINS")

    @property
    def allowed_hosts_list(self) -> list[str]:
        return [h.strip() for h in self.allowed_hosts.split(",") if h.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


class DatabaseSettings(_EnvBaseSettings):
    url: PostgresDsn = Field(alias="DATABASE_URL")
    url_sync: PostgresDsn = Field(alias="DATABASE_URL_SYNC")
    pool_size: int = Field(default=10, alias="DATABASE_POOL_SIZE")
    max_overflow: int = Field(default=20, alias="DATABASE_MAX_OVERFLOW")
    echo: bool = Field(default=False, alias="DATABASE_ECHO")


class RedisSettings(_EnvBaseSettings):
    url: RedisDsn = Field(alias="REDIS_URL")


class QdrantSettings(_EnvBaseSettings):
    host: str = Field(default="localhost", alias="QDRANT_HOST")
    port: int = Field(default=6333, alias="QDRANT_PORT")
    grpc_port: int = Field(default=6334, alias="QDRANT_GRPC_PORT")
    api_key: str | None = Field(default=None, alias="QDRANT_API_KEY")
    collection_prefix: str = Field(default="drassist", alias="QDRANT_COLLECTION_PREFIX")


class CelerySettings(_EnvBaseSettings):
    broker_url: str = Field(alias="CELERY_BROKER_URL")
    result_backend: str = Field(alias="CELERY_RESULT_BACKEND")
    task_always_eager: bool = Field(default=False, alias="CELERY_TASK_ALWAYS_EAGER")


class MinioSettings(_EnvBaseSettings):
    endpoint: str = Field(alias="MINIO_ENDPOINT")
    access_key: str = Field(alias="MINIO_ACCESS_KEY")
    secret_key: str = Field(alias="MINIO_SECRET_KEY")
    bucket_name: str = Field(default="drassist", alias="MINIO_BUCKET_NAME")
    use_ssl: bool = Field(default=False, alias="MINIO_USE_SSL")


class LocalStorageSettings(_EnvBaseSettings):
    """Configures `app.infrastructure.storage.local_storage_provider
    .LocalStorageProvider` — the File Upload / Storage module's only
    concrete `StoragePort` adapter. `base_path` is a filesystem root all
    buckets are created under (e.g. `{base_path}/{bucket}/{object_name}`);
    `max_upload_size_bytes` is an operational ceiling enforced by the
    Documents module's upload use case, not a `StoragePort` concern
    (a future S3/Azure/GCS adapter would enforce its own provider-specific
    limit instead, so this setting deliberately isn't part of the port).
    """

    base_path: str = Field(default="./storage", alias="LOCAL_STORAGE_BASE_PATH")
    max_upload_size_bytes: int = Field(
        default=52_428_800, alias="LOCAL_STORAGE_MAX_UPLOAD_SIZE_BYTES"
    )


class GeminiSettings(_EnvBaseSettings):
    api_key: str = Field(alias="GEMINI_API_KEY")
    model: str = Field(default="gemini-2.5-pro", alias="GEMINI_MODEL")


class WhisperSettings(_EnvBaseSettings):
    model_size: str = Field(default="medium", alias="FASTER_WHISPER_MODEL_SIZE")
    device: Literal["cpu", "cuda"] = Field(default="cpu", alias="FASTER_WHISPER_DEVICE")
    compute_type: str = Field(default="int8", alias="FASTER_WHISPER_COMPUTE_TYPE")


class PaddleOCRSettings(_EnvBaseSettings):
    lang: str = Field(default="en", alias="PADDLEOCR_LANG")
    use_gpu: bool = Field(default=False, alias="PADDLEOCR_USE_GPU")


class JWTSettings(_EnvBaseSettings):
    algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS")


class ObservabilitySettings(_EnvBaseSettings):
    sentry_dsn: str | None = Field(default=None, alias="SENTRY_DSN")
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None, alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )


class Settings(_EnvBaseSettings):
    """Root settings object. Instantiate once via `get_settings()`."""

    environment: Environment = Field(default="development", alias="ENVIRONMENT")
    project_name: str = Field(default="DrAssist", alias="PROJECT_NAME")
    api_version: str = Field(default="v1", alias="API_VERSION")
    timezone: str = Field(default="UTC", alias="TIMEZONE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: LogFormat = Field(default="json", alias="LOG_FORMAT")

    backend: BackendSettings = Field(default_factory=BackendSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    qdrant: QdrantSettings = Field(default_factory=QdrantSettings)
    celery: CelerySettings = Field(default_factory=CelerySettings)
    minio: MinioSettings = Field(default_factory=MinioSettings)
    local_storage: LocalStorageSettings = Field(default_factory=LocalStorageSettings)
    gemini: GeminiSettings = Field(default_factory=GeminiSettings)
    whisper: WhisperSettings = Field(default_factory=WhisperSettings)
    paddleocr: PaddleOCRSettings = Field(default_factory=PaddleOCRSettings)
    jwt: JWTSettings = Field(default_factory=JWTSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = value.upper()
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}, got {value!r}")
        return upper

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide cached Settings instance."""
    return Settings()

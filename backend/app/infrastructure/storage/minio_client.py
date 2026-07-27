"""MinIO client factory.

Provides the raw SDK client only. A concrete `StoragePort`
(`app/application/interfaces/storage_port.py`) implementation that wraps
this client belongs in `app/infrastructure/repositories/` or a sibling
adapter module once upload/download flows are implemented.
"""

from functools import lru_cache

from minio import Minio

from app.core.config import get_settings


@lru_cache
def get_minio_client() -> Minio:
    settings = get_settings()
    return Minio(
        settings.minio.endpoint,
        access_key=settings.minio.access_key,
        secret_key=settings.minio.secret_key,
        secure=settings.minio.use_ssl,
    )

"""Qdrant client factory.

Provides the raw SDK client only. A concrete `VectorStorePort`
(`app/application/interfaces/vector_store_port.py`) implementation that
wraps this client belongs in `app/infrastructure/repositories/` once
collection schemas and embedding flows are defined.
"""

from functools import lru_cache

from qdrant_client import QdrantClient

from app.core.config import get_settings


@lru_cache
def get_qdrant_client() -> QdrantClient:
    settings = get_settings()
    return QdrantClient(
        host=settings.qdrant.host,
        port=settings.qdrant.port,
        grpc_port=settings.qdrant.grpc_port,
        api_key=settings.qdrant.api_key,
    )

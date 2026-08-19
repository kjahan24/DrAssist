"""Qdrant client factories.

Provides the raw SDK clients only. The concrete `VectorStorePort`
(`app/shared/application/vector_store_port.py`) implementation that wraps
the async client lives alongside it in this same package —
`qdrant_vector_store.QdrantVectorStore` — since collection schemas and
embedding flows are now defined (community_ai, Phase 5.10).
"""

from functools import lru_cache

from qdrant_client import AsyncQdrantClient, QdrantClient

from app.core.config import get_settings


@lru_cache
def get_qdrant_client() -> QdrantClient:
    settings = get_settings()
    return QdrantClient(
        host=settings.qdrant.host,
        port=settings.qdrant.port,
        grpc_port=settings.qdrant.grpc_port,
        api_key=settings.qdrant.api_key,
        https=False,
    )


@lru_cache
def get_async_qdrant_client() -> AsyncQdrantClient:
    """`https=False` is explicit, not the default: `qdrant-client` treats
    a non-`None` `api_key` as a signal to assume TLS (the shape of
    Qdrant Cloud) unless told otherwise. `docker-compose.yml`'s `qdrant`
    service (`QDRANT__SERVICE__API_KEY` set, but no TLS termination) is
    plain HTTP with an API key — the opposite combination — so this must
    be forced off or every request fails with an SSL handshake error."""
    settings = get_settings()
    return AsyncQdrantClient(
        host=settings.qdrant.host,
        port=settings.qdrant.port,
        grpc_port=settings.qdrant.grpc_port,
        api_key=settings.qdrant.api_key,
        https=False,
    )

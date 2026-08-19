"""`QdrantVectorStore` — the first concrete `VectorStorePort`
(`app.shared.application.vector_store_port.VectorStorePort`) implementation
in the codebase. Wraps `AsyncQdrantClient` (`qdrant_client.py`'s
`get_async_qdrant_client()` factory) behind the port's exact four-method
contract: `upsert`/`search`/`delete`/`retrieve`.

Collections are provisioned lazily on first `upsert` — there is no prior
migration-style provisioning precedent for Qdrant anywhere in this
codebase, so `_ensure_collection` checks `collection_exists` and creates
one sized to the given vector's own dimensionality (`Distance.COSINE`,
the standard choice for text-embedding similarity) the first time a given
collection name is written to. Callers pass an already-prefixed
collection name (e.g. via `settings.qdrant.collection_prefix`); this
class does not itself apply the prefix, keeping it a thin, generic
adapter reusable by any future feature, not just `community_ai`.

`search` never trusts the returned payload as authoritative for anything
beyond what it literally stored — callers (e.g. `community_ai`'s
`DefaultSimilarDiscussionSearch`) are responsible for re-validating any
returned candidate against its true source of record before use.

**Point ID translation**: `VectorStorePort.upsert`/`retrieve`/`delete` all
take an arbitrary `vector_id: str` — Qdrant itself only accepts an
unsigned integer or a UUID as a point ID and rejects anything else with
an HTTP 400 (confirmed via this class's own integration boundary tests:
`community_ai`'s `DefaultSimilarDiscussionSearch` constructs ids like
`"post:3fa85f64-...")`, not a bare UUID). `_point_id` deterministically
maps every caller-supplied string to a UUID5 (namespaced, so the same
string always maps to the same point — upsert-by-same-key idempotency is
preserved) before it ever reaches the SDK. This translation is entirely
internal to this adapter: `search`'s returned `"id"` is therefore the
derived UUID, not the caller's original string, which is why no caller
in this codebase treats a search result's `id` as meaningful — the
`payload` is the source of truth for identity (see `search`'s own
paragraph above).
"""

import uuid
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.shared.application.vector_store_port import VectorStorePort

_POINT_ID_NAMESPACE = uuid.UUID("7b3f2c1a-6e4d-4a8b-9c2f-1d5e8a3b6f90")


def _point_id(vector_id: str) -> str:
    return str(uuid.uuid5(_POINT_ID_NAMESPACE, vector_id))


class QdrantVectorStore(VectorStorePort):
    def __init__(self, client: AsyncQdrantClient) -> None:
        self._client = client

    async def upsert(
        self,
        *,
        collection: str,
        vector_id: str,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None:
        await self._ensure_collection(collection, dimension=len(vector))
        await self._client.upsert(
            collection_name=collection,
            points=[PointStruct(id=_point_id(vector_id), vector=vector, payload=payload)],
            wait=True,
        )

    async def search(
        self, *, collection: str, query_vector: list[float], top_k: int = 5
    ) -> list[dict[str, Any]]:
        if not await self._client.collection_exists(collection):
            return []
        results = await self._client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True,
        )
        return [
            {"id": str(point.id), "score": point.score, "payload": point.payload or {}}
            for point in results
        ]

    async def delete(self, *, collection: str, vector_id: str) -> None:
        if not await self._client.collection_exists(collection):
            return
        await self._client.delete(
            collection_name=collection, points_selector=[_point_id(vector_id)], wait=True
        )

    async def retrieve(self, *, collection: str, vector_id: str) -> list[float] | None:
        if not await self._client.collection_exists(collection):
            return None
        records = await self._client.retrieve(
            collection_name=collection, ids=[_point_id(vector_id)], with_vectors=True
        )
        if not records:
            return None
        vector = records[0].vector
        if not isinstance(vector, list):
            return None
        components: list[float] = []
        for component in vector:
            if not isinstance(component, int | float):
                return None
            components.append(float(component))
        return components

    async def _ensure_collection(self, collection: str, *, dimension: int) -> None:
        if await self._client.collection_exists(collection):
            return
        await self._client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
        )

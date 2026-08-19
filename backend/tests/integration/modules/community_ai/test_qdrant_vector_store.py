"""Integration boundary tests for `QdrantVectorStore` against a real
Qdrant instance (`QDRANT_HOST`/`QDRANT_PORT`, the `drassist-qdrant`
service defined in `docker-compose.yml`) — this task's own required
"Qdrant/vector integration boundary tests" quality gate. Unlike the unit
tests in `tests/unit/modules/community_ai/infrastructure
/test_embedding_similarity_search.py` (which use an in-memory
`FakeVectorStore` and never touch a network), these confirm the actual
`AsyncQdrantClient` wiring — lazy collection creation, `upsert`/`search`/
`retrieve`/`delete` — round-trips correctly against the real service.

Each test uses a uniquely-suffixed collection name so tests can run
repeatedly without colliding; a fixture drops the collection afterward
(unlike Postgres rows, leaving Qdrant collections behind across repeated
runs is unbounded growth, not just clutter).

Builds its own `AsyncQdrantClient` per test rather than reusing the
process-wide `get_async_qdrant_client()` singleton — see
`tests.integration.modules.organization.conftest`'s own `db_session`
docstring for the identical "one event loop per test function" reasoning:
an `lru_cache`d async client's underlying HTTP connection is bound to the
event loop of whichever test first constructed it, and pytest-asyncio
tears that loop down at the end of each test function, so a second test
reusing the cached client fails with "Event loop is closed".
"""

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest_asyncio
from qdrant_client import AsyncQdrantClient

from app.core.config import get_settings
from app.infrastructure.vector_store.qdrant_vector_store import QdrantVectorStore


@pytest_asyncio.fixture
async def qdrant_client() -> AsyncIterator[AsyncQdrantClient]:
    settings = get_settings()
    client = AsyncQdrantClient(
        host=settings.qdrant.host,
        port=settings.qdrant.port,
        grpc_port=settings.qdrant.grpc_port,
        api_key=settings.qdrant.api_key,
        https=False,
    )
    try:
        yield client
    finally:
        await client.close()


@pytest_asyncio.fixture
async def collection_name(qdrant_client: AsyncQdrantClient) -> AsyncIterator[str]:
    name = f"test_community_ai_{uuid4().hex[:12]}"
    yield name
    if await qdrant_client.collection_exists(name):
        await qdrant_client.delete_collection(name)


class TestQdrantVectorStoreRoundTrip:
    async def test_upsert_then_retrieve_returns_the_same_direction(
        self, qdrant_client: AsyncQdrantClient, collection_name: str
    ) -> None:
        """Qdrant normalizes stored vectors under `Distance.COSINE`
        (confirmed here, not merely assumed) — so the retrieved vector is
        the unit vector in the same direction as the input, not a
        byte-for-byte copy of the un-normalized components."""
        store = QdrantVectorStore(qdrant_client)
        vector = [0.1, 0.2, 0.3, 0.4]

        await store.upsert(
            collection=collection_name,
            vector_id="point-1",
            vector=vector,
            payload={"target_type": "post", "target_id": str(uuid4())},
        )

        retrieved = await store.retrieve(collection=collection_name, vector_id="point-1")
        assert retrieved is not None
        magnitude = sum(v * v for v in vector) ** 0.5
        expected = [v / magnitude for v in vector]
        assert [round(v, 4) for v in retrieved] == [round(v, 4) for v in expected]

    async def test_retrieve_returns_none_for_an_unknown_collection(
        self, qdrant_client: AsyncQdrantClient, collection_name: str
    ) -> None:
        store = QdrantVectorStore(qdrant_client)
        result = await store.retrieve(collection=collection_name, vector_id="never-upserted")
        assert result is None

    async def test_search_finds_a_nearby_point_and_carries_its_payload(
        self, qdrant_client: AsyncQdrantClient, collection_name: str
    ) -> None:
        store = QdrantVectorStore(qdrant_client)
        target_id = str(uuid4())
        await store.upsert(
            collection=collection_name,
            vector_id="source",
            vector=[1.0, 0.0, 0.0],
            payload={"target_type": "post", "target_id": str(uuid4())},
        )
        await store.upsert(
            collection=collection_name,
            vector_id="neighbor",
            vector=[0.9, 0.1, 0.0],
            payload={"target_type": "question", "target_id": target_id},
        )

        results = await store.search(
            collection=collection_name, query_vector=[1.0, 0.0, 0.0], top_k=5
        )

        assert len(results) == 2
        assert all(isinstance(r["score"], float) for r in results)
        # `id` is this adapter's own internally-derived point id, not the
        # caller's original `vector_id` — see `_point_id`'s own docstring
        # for why identity is carried through `payload` instead.
        payloads_by_target_type = {r["payload"]["target_type"]: r["payload"] for r in results}
        assert payloads_by_target_type["question"] == {
            "target_type": "question",
            "target_id": target_id,
        }

    async def test_search_against_a_never_created_collection_returns_empty(
        self, qdrant_client: AsyncQdrantClient, collection_name: str
    ) -> None:
        store = QdrantVectorStore(qdrant_client)
        results = await store.search(collection=collection_name, query_vector=[1.0, 0.0], top_k=5)
        assert results == []

    async def test_delete_removes_the_point(
        self, qdrant_client: AsyncQdrantClient, collection_name: str
    ) -> None:
        store = QdrantVectorStore(qdrant_client)
        await store.upsert(
            collection=collection_name,
            vector_id="to-delete",
            vector=[0.5, 0.5],
            payload={},
        )

        await store.delete(collection=collection_name, vector_id="to-delete")

        assert await store.retrieve(collection=collection_name, vector_id="to-delete") is None

    async def test_delete_against_a_never_created_collection_is_a_no_op(
        self, qdrant_client: AsyncQdrantClient, collection_name: str
    ) -> None:
        store = QdrantVectorStore(qdrant_client)
        await store.delete(collection=collection_name, vector_id="anything")

    async def test_accepts_the_colon_separated_id_shape_community_ai_actually_uses(
        self, qdrant_client: AsyncQdrantClient, collection_name: str
    ) -> None:
        """Qdrant itself only accepts an unsigned integer or a UUID as a
        point id and rejects anything else with an HTTP 400 — this
        specific id shape (`"post:<uuid>"`, from
        `DefaultSimilarDiscussionSearch._vector_id`) is exactly what first
        caught that as a real bug (see `qdrant_vector_store.py`'s own
        `_point_id` docstring), so it is pinned here as a regression
        test."""
        store = QdrantVectorStore(qdrant_client)
        vector_id = f"post:{uuid4()}"

        await store.upsert(
            collection=collection_name, vector_id=vector_id, vector=[0.2, 0.4], payload={}
        )

        assert await store.retrieve(collection=collection_name, vector_id=vector_id) is not None

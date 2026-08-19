"""Unit tests for `DefaultSimilarDiscussionSearch`, using a fake
`VectorStorePort`/`AIGatewayPort` — never a real Qdrant instance (that is
covered separately by the integration-layer "Qdrant/vector integration
boundary tests")."""

from typing import Any
from uuid import uuid4

from app.modules.ai.public.dto import AIModel, AIProviderType
from app.modules.community_ai.domain.enums import CommunityContentTargetType
from app.modules.community_ai.infrastructure.vector_search.embedding_similarity_search import (
    DefaultSimilarDiscussionSearch,
)
from app.shared.application.vector_store_port import VectorStorePort
from tests.unit.modules.community_ai.application.fakes import FakeAIGateway


class FakeVectorStore(VectorStorePort):
    def __init__(self) -> None:
        self._points: dict[str, dict[str, dict[str, Any]]] = {}

    async def upsert(
        self, *, collection: str, vector_id: str, vector: list[float], payload: dict[str, Any]
    ) -> None:
        self._points.setdefault(collection, {})[vector_id] = {
            "vector": vector,
            "payload": payload,
        }

    async def search(
        self, *, collection: str, query_vector: list[float], top_k: int = 5
    ) -> list[dict[str, Any]]:
        points = self._points.get(collection, {})
        return [
            {"id": vector_id, "score": 1.0, "payload": data["payload"]}
            for vector_id, data in list(points.items())[:top_k]
        ]

    async def delete(self, *, collection: str, vector_id: str) -> None:
        self._points.get(collection, {}).pop(vector_id, None)

    async def retrieve(self, *, collection: str, vector_id: str) -> list[float] | None:
        point = self._points.get(collection, {}).get(vector_id)
        return point["vector"] if point is not None else None


def _search(
    *, vector_store: FakeVectorStore | None = None, ai_gateway: FakeAIGateway | None = None
) -> tuple[DefaultSimilarDiscussionSearch, FakeVectorStore]:
    store = vector_store or FakeVectorStore()
    search = DefaultSimilarDiscussionSearch(
        ai_gateway=ai_gateway or FakeAIGateway(),
        vector_store=store,
        embedding_model=AIModel(
            provider=AIProviderType.MOCK, name="mock-embed", supports_embeddings=True
        ),
        collection_prefix="test",
    )
    return search, store


class TestIndexTarget:
    async def test_upserts_into_a_per_organization_collection(self) -> None:
        search, store = _search()
        org_id, target_id = uuid4(), uuid4()

        await search.index_target(
            target_type=CommunityContentTargetType.POST,
            target_id=target_id,
            organization_id=org_id,
            text="Some discussion text",
        )

        collection = f"test_community_discussions_{org_id}"
        assert collection in store._points
        assert f"post:{target_id}" in store._points[collection]

    async def test_skips_indexing_blank_text(self) -> None:
        search, store = _search()
        await search.index_target(
            target_type=CommunityContentTargetType.POST,
            target_id=uuid4(),
            organization_id=uuid4(),
            text="   ",
        )
        assert store._points == {}


class TestFindSimilar:
    async def test_returns_empty_tuple_when_the_source_has_never_been_indexed(self) -> None:
        search, _ = _search()
        result = await search.find_similar(
            target_type=CommunityContentTargetType.POST,
            target_id=uuid4(),
            organization_id=uuid4(),
            limit=10,
        )
        assert result == ()

    async def test_excludes_the_source_itself_from_results(self) -> None:
        search, _ = _search()
        org_id, source_id = uuid4(), uuid4()
        await search.index_target(
            target_type=CommunityContentTargetType.POST,
            target_id=source_id,
            organization_id=org_id,
            text="Source text",
        )

        result = await search.find_similar(
            target_type=CommunityContentTargetType.POST,
            target_id=source_id,
            organization_id=org_id,
            limit=10,
        )

        assert result == ()

    async def test_returns_another_indexed_target_as_a_candidate(self) -> None:
        search, _ = _search()
        org_id, source_id, other_id = uuid4(), uuid4(), uuid4()
        await search.index_target(
            target_type=CommunityContentTargetType.POST,
            target_id=source_id,
            organization_id=org_id,
            text="Source text",
        )
        await search.index_target(
            target_type=CommunityContentTargetType.QUESTION,
            target_id=other_id,
            organization_id=org_id,
            text="Other text",
        )

        result = await search.find_similar(
            target_type=CommunityContentTargetType.POST,
            target_id=source_id,
            organization_id=org_id,
            limit=10,
        )

        assert len(result) == 1
        assert result[0].target_id == other_id
        assert result[0].target_type is CommunityContentTargetType.QUESTION
        assert 0.0 <= result[0].similarity_score <= 1.0

    async def test_organizations_are_isolated_by_collection(self) -> None:
        search, _ = _search()
        org_a, org_b = uuid4(), uuid4()
        source_id = uuid4()
        await search.index_target(
            target_type=CommunityContentTargetType.POST,
            target_id=source_id,
            organization_id=org_a,
            text="Org A source",
        )
        await search.index_target(
            target_type=CommunityContentTargetType.POST,
            target_id=uuid4(),
            organization_id=org_b,
            text="Org B other",
        )

        result = await search.find_similar(
            target_type=CommunityContentTargetType.POST,
            target_id=source_id,
            organization_id=org_a,
            limit=10,
        )

        assert result == ()

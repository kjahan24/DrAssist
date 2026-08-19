"""`DefaultSimilarDiscussionSearch` — the one concrete implementation of
`SimilarDiscussionSearchPort` (`application/ports.py`). Combines
`AIGatewayPort.generate_embedding` (never a provider SDK directly) with
`app.shared.application.vector_store_port.VectorStorePort`
(`app.infrastructure.vector_store.qdrant_vector_store.QdrantVectorStore` —
the first concrete implementation of that port in this codebase) rather
than talking to Qdrant directly, so this module never duplicates vector-
store infrastructure.

**Tenant isolation is structural, not just a re-check**: each
organization gets its own Qdrant collection
(`"{prefix}_community_discussions_{organization_id}"`), so a search can
never surface another tenant's vectors even before
`FindSimilarDiscussionsService._validate_candidates` re-confirms every
candidate through the real query ports. `VectorStorePort.search` takes no
payload filter, which is exactly why per-tenant collections — not a
shared collection plus a filter — were chosen.

`find_similar` never re-embeds: `index_target` must have already upserted
the source's vector (see `FindSimilarDiscussionsService`'s own docstring
for why `index_target` always runs immediately before `find_similar` in
the same request); `find_similar` looks that stored vector back up via
`VectorStorePort.retrieve` and uses it as the query vector. If it isn't
there yet, this returns an empty tuple rather than raising — the "Handle
missing embeddings gracefully" requirement `application/ports.py`'s own
docstring already commits to.

Qdrant's COSINE distance score is a raw cosine similarity in `[-1, 1]`;
`SimilarDiscussion.similarity_score` requires `[0, 1]` (see
`domain/value_objects.py`), so scores are linearly rescaled
(`(score + 1) / 2`), not merely clamped, to preserve relative ranking.
"""

from uuid import UUID

from app.modules.ai.public.dto import AIModel, EmbeddingRequest
from app.modules.ai.public.interfaces import AIGatewayPort
from app.modules.community_ai.application.ports import SimilarDiscussionSearchPort
from app.modules.community_ai.domain.enums import CommunityContentTargetType
from app.modules.community_ai.domain.value_objects import SimilarDiscussion
from app.shared.application.vector_store_port import VectorStorePort


def _vector_id(target_type: CommunityContentTargetType, target_id: UUID) -> str:
    return f"{target_type.value}:{target_id}"


def _rescale_cosine_score(score: float) -> float:
    rescaled = (score + 1.0) / 2.0
    return max(0.0, min(1.0, rescaled))


class DefaultSimilarDiscussionSearch(SimilarDiscussionSearchPort):
    def __init__(
        self,
        *,
        ai_gateway: AIGatewayPort,
        vector_store: VectorStorePort,
        embedding_model: AIModel,
        collection_prefix: str,
    ) -> None:
        self._ai_gateway = ai_gateway
        self._vector_store = vector_store
        self._embedding_model = embedding_model
        self._collection_prefix = collection_prefix

    def _collection_name(self, organization_id: UUID) -> str:
        return f"{self._collection_prefix}_community_discussions_{organization_id}"

    async def index_target(
        self,
        *,
        target_type: CommunityContentTargetType,
        target_id: UUID,
        organization_id: UUID,
        text: str,
    ) -> None:
        if not text.strip():
            return
        vector = await self._embed(text)
        await self._vector_store.upsert(
            collection=self._collection_name(organization_id),
            vector_id=_vector_id(target_type, target_id),
            vector=vector,
            payload={"target_type": target_type.value, "target_id": str(target_id)},
        )

    async def find_similar(
        self,
        *,
        target_type: CommunityContentTargetType,
        target_id: UUID,
        organization_id: UUID,
        limit: int,
    ) -> tuple[SimilarDiscussion, ...]:
        collection = self._collection_name(organization_id)
        source_vector = await self._vector_store.retrieve(
            collection=collection, vector_id=_vector_id(target_type, target_id)
        )
        if source_vector is None:
            return ()

        raw_results = await self._vector_store.search(
            collection=collection, query_vector=source_vector, top_k=limit + 1
        )
        source_key = (target_type.value, str(target_id))
        candidates: list[SimilarDiscussion] = []
        for item in raw_results:
            payload = item.get("payload") or {}
            raw_target_type = payload.get("target_type")
            raw_target_id = payload.get("target_id")
            if raw_target_type is None or raw_target_id is None:
                continue
            if (raw_target_type, raw_target_id) == source_key:
                continue
            try:
                candidate_type = CommunityContentTargetType(raw_target_type)
                candidate_id = UUID(str(raw_target_id))
            except ValueError:
                continue
            score = _rescale_cosine_score(float(item.get("score", 0.0)))
            candidates.append(
                SimilarDiscussion(
                    target_type=candidate_type, target_id=candidate_id, similarity_score=score
                )
            )
            if len(candidates) >= limit:
                break
        return tuple(candidates)

    async def _embed(self, text: str) -> list[float]:
        response = await self._ai_gateway.generate_embedding(
            EmbeddingRequest(input_texts=(text,), model=self._embedding_model)
        )
        return list(response.embeddings[0])

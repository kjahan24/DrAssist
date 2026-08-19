"""Application-layer ports for the Community AI Features module.

`CommunityAIGeneratorPort` wraps `app.modules.ai.public.interfaces
.AIGatewayPort.generate_chat_completion` — the same "define your own
module-local generator port, implement it against `AIGatewayPort`, never
call a provider SDK directly" shape every `*_ai` module in this codebase
follows (e.g. `app.modules.medical_reasoning_ai.application.ports
.MedicalReasoningPort`). Its concrete implementation is
`infrastructure/generation/community_ai_generator.py`.

`SimilarDiscussionSearchPort` wraps both `AIGatewayPort.generate_embedding`
and `app.shared.application.vector_store_port.VectorStorePort` — this
module's own seam over embedding+vector-search, since neither Qdrant nor
`VectorStorePort` has any prior concrete implementation to depend on
directly (see `infrastructure/vector_search/embedding_similarity_search
.py`'s own docstring).

`TrustedResourceCatalogPort` is the mechanism that makes "Do NOT fabricate
medical sources" structural: the AI ranks/explains sources drawn from this
port's own known, curated catalog — it is never asked to invent a URL —
see `domain/value_objects.py::TrustedMedicalSource`'s own docstring. "so
approved/trusted medical sources can be configured without hard-coding a
single provider" (this task's own wording) is satisfied by this being a
swappable port, not a single hard-coded implementation baked into the
generator itself.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from uuid import UUID

from app.modules.community_ai.application.dto import GenerationMetadata
from app.modules.community_ai.domain.enums import CommunityContentTargetType
from app.modules.community_ai.domain.value_objects import (
    CommunityDiscussionSummary,
    MisinformationAssessment,
    SimilarDiscussion,
    TrustedMedicalSource,
    TrustedResourceRecommendation,
)


class CommunityAIGeneratorPort(ABC):
    @abstractmethod
    async def generate_summary(
        self, *, title: str | None, text: str
    ) -> tuple[CommunityDiscussionSummary, GenerationMetadata]: ...

    @abstractmethod
    async def generate_misinformation_assessment(
        self, *, title: str | None, text: str
    ) -> tuple[MisinformationAssessment, GenerationMetadata]: ...

    @abstractmethod
    async def generate_resource_recommendations(
        self, *, title: str | None, text: str, catalog: Sequence[TrustedMedicalSource]
    ) -> tuple[tuple[TrustedResourceRecommendation, ...], GenerationMetadata]: ...


class SimilarDiscussionSearchPort(ABC):
    @abstractmethod
    async def index_target(
        self,
        *,
        target_type: CommunityContentTargetType,
        target_id: UUID,
        organization_id: UUID,
        text: str,
    ) -> None:
        """Embed `text` and upsert it into the vector store under
        `(target_type, target_id)` — called lazily, on demand, by
        `FindSimilarDiscussionsService` for the source target it is about
        to search from. See that service's own docstring for why this is
        an index-on-read design rather than an event-driven indexing
        pipeline."""
        ...

    @abstractmethod
    async def find_similar(
        self,
        *,
        target_type: CommunityContentTargetType,
        target_id: UUID,
        organization_id: UUID,
        limit: int,
    ) -> tuple[SimilarDiscussion, ...]:
        """Ranked candidates similar to `(target_type, target_id)`,
        excluding the source itself, scoped to `organization_id`. Returns
        an empty tuple — never raises — when the source has no embedding
        yet or the vector store has no other indexed candidates, per this
        task's own "Handle missing embeddings gracefully" requirement."""
        ...


class TrustedResourceCatalogPort(ABC):
    @abstractmethod
    async def list_sources(self, *, keywords: Sequence[str] = ()) -> Sequence[TrustedMedicalSource]:
        """Every source relevant to `keywords` (topic-tag overlap,
        highest-overlap first); with no keywords, or when nothing
        matches, returns the full curated catalog rather than an empty
        sequence — there is always a reasonable, non-fabricated set of
        general trusted medical resources to offer."""
        ...

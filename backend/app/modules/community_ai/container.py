"""Module composition root for the Community AI Features module's
process-lifetime, session-independent components.

`DefaultCommunityAIGenerator`/`DefaultSimilarDiscussionSearch`/
`StaticTrustedResourceCatalog`/`QdrantVectorStore` hold no per-request
state (they call `AIGatewayPort`/Qdrant, never a SQL session), so each is
exposed as an `lru_cache`d singleton — the same shape
`app.modules.icd10_ai.container` already establishes for its own
generation-only components. Unlike `icd10_ai`, this module also persists
(`AICommunityAnalysisRepository`/`UnitOfWork` need a request-scoped
`AsyncSession`) — those are wired per-request in
`presentation/dependencies.py` instead, exactly as
`community_moderation`'s own `presentation/dependencies.py` does for its
own DB-backed repositories.

`build_community_ai_facade(session)` is the per-request factory for this
module's own public surface (`public/facade.py::CommunityAIFacade`) — the
same "one `build_<module>_facade(session)` a peer module calls, never
constructing the facade directly" rule every prior module's own
`container.py` establishes.
"""

from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.infrastructure.vector_store.qdrant_client import get_async_qdrant_client
from app.infrastructure.vector_store.qdrant_vector_store import QdrantVectorStore
from app.modules.ai.container import get_ai_gateway_facade, get_prompt_registry
from app.modules.community_ai.application.ports import (
    CommunityAIGeneratorPort,
    SimilarDiscussionSearchPort,
    TrustedResourceCatalogPort,
)
from app.modules.community_ai.infrastructure.generation.community_ai_generator import (
    DefaultCommunityAIGenerator,
)
from app.modules.community_ai.infrastructure.provider_selection import (
    resolve_default_ai_model,
    resolve_default_embedding_model,
)
from app.modules.community_ai.infrastructure.repositories import (
    SqlAlchemyAICommunityAnalysisRepository,
)
from app.modules.community_ai.infrastructure.resources.static_trusted_resource_catalog import (
    StaticTrustedResourceCatalog,
)
from app.modules.community_ai.infrastructure.vector_search.embedding_similarity_search import (
    DefaultSimilarDiscussionSearch,
)
from app.modules.community_ai.public.facade import CommunityAIFacade
from app.shared.application.vector_store_port import VectorStorePort


@lru_cache
def get_vector_store() -> VectorStorePort:
    return QdrantVectorStore(get_async_qdrant_client())


@lru_cache
def get_community_ai_generator() -> CommunityAIGeneratorPort:
    settings = get_settings()
    return DefaultCommunityAIGenerator(
        ai_gateway=get_ai_gateway_facade(),
        prompt_registry=get_prompt_registry(),
        default_model=resolve_default_ai_model(settings),
    )


@lru_cache
def get_similar_discussion_search() -> SimilarDiscussionSearchPort:
    settings = get_settings()
    return DefaultSimilarDiscussionSearch(
        ai_gateway=get_ai_gateway_facade(),
        vector_store=get_vector_store(),
        embedding_model=resolve_default_embedding_model(settings),
        collection_prefix=settings.qdrant.collection_prefix,
    )


@lru_cache
def get_trusted_resource_catalog() -> TrustedResourceCatalogPort:
    return StaticTrustedResourceCatalog()


def build_community_ai_facade(session: AsyncSession) -> CommunityAIFacade:
    """Construct a `CommunityAIFacade` wired to `session`."""
    return CommunityAIFacade(analysis_repository=SqlAlchemyAICommunityAnalysisRepository(session))

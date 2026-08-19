"""`StaticTrustedResourceCatalog` — the one concrete implementation of
`TrustedResourceCatalogPort` (`application/ports.py`). A small, fixed,
hand-curated list of genuinely real, well-known trusted medical
organizations and their real URLs — never AI-generated, never fetched
from an external index — which is the structural half of "Do NOT
fabricate medical sources" (the other half is
`infrastructure/generation/community_ai_generator.py`'s own post-filter
against this same catalog's URLs).

Ranking is a simple topic-tag overlap count, ties broken by the catalog's
own declaration order (stable sort) — there is no precedent anywhere in
this codebase for a more elaborate relevance-ranking algorithm for a
handful of static entries, and this task does not ask for one. With no
keywords, or when nothing overlaps, the full catalog is returned (per
`TrustedResourceCatalogPort.list_sources`'s own docstring) rather than an
empty sequence, since a general set of trusted resources is always a
reasonable, non-fabricated answer.
"""

from collections.abc import Sequence

from app.modules.community_ai.application.ports import TrustedResourceCatalogPort
from app.modules.community_ai.domain.enums import ResourceType
from app.modules.community_ai.domain.value_objects import TrustedMedicalSource

_CATALOG: tuple[TrustedMedicalSource, ...] = (
    TrustedMedicalSource(
        title="MedlinePlus",
        url="https://medlineplus.gov",
        resource_type=ResourceType.WEBSITE,
        topic_tags=("general health", "conditions", "medications", "patient education"),
    ),
    TrustedMedicalSource(
        title="Centers for Disease Control and Prevention (CDC)",
        url="https://www.cdc.gov",
        resource_type=ResourceType.ORGANIZATION,
        topic_tags=("infectious disease", "public health", "vaccination", "prevention"),
    ),
    TrustedMedicalSource(
        title="World Health Organization (WHO)",
        url="https://www.who.int",
        resource_type=ResourceType.ORGANIZATION,
        topic_tags=("global health", "infectious disease", "guidelines", "outbreaks"),
    ),
    TrustedMedicalSource(
        title="Mayo Clinic",
        url="https://www.mayoclinic.org",
        resource_type=ResourceType.WEBSITE,
        topic_tags=("symptoms", "conditions", "treatment", "patient education"),
    ),
    TrustedMedicalSource(
        title="Cochrane Library",
        url="https://www.cochranelibrary.com",
        resource_type=ResourceType.RESEARCH_PAPER,
        topic_tags=("evidence review", "systematic review", "treatment efficacy"),
    ),
    TrustedMedicalSource(
        title="PubMed",
        url="https://pubmed.ncbi.nlm.nih.gov",
        resource_type=ResourceType.RESEARCH_PAPER,
        topic_tags=("research", "clinical studies", "medical literature"),
    ),
)


class StaticTrustedResourceCatalog(TrustedResourceCatalogPort):
    async def list_sources(self, *, keywords: Sequence[str] = ()) -> Sequence[TrustedMedicalSource]:
        if not keywords:
            return _CATALOG

        normalized_keywords = {keyword.strip().lower() for keyword in keywords if keyword.strip()}
        if not normalized_keywords:
            return _CATALOG

        scored: list[tuple[int, TrustedMedicalSource]] = []
        for source in _CATALOG:
            tags = {tag.lower() for tag in source.topic_tags}
            overlap = len(tags & normalized_keywords)
            if overlap > 0:
                scored.append((overlap, source))

        if not scored:
            return _CATALOG

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [source for _, source in scored]

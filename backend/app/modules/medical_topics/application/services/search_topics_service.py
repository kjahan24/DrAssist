"""`SearchTopicsService` — free-text search over topic name/description,
widened to also match topic aliases/synonyms (this task's own "Topic
aliases"/"Topic synonyms" FEATURES bullets exist specifically so a search
for a colloquial term still finds the topic that owns it as an alias).
Restricted to `PUBLISHED`+`PUBLIC` topics only — the public discovery
surface, distinct from the generic, unrestricted `ListTopicsService`
(the management/catalog view) — see `TopicVisibility`'s own docstring.

Alias matches are appended after the primary name/description matches,
up to the page's remaining capacity, rather than merged into one
database-level ranked query — combining two independently-paginated
result sets exactly (with a single, precise running `total`) would need
a single UNIONed query neither `MedicalTopicRepository.search` nor
`MedicalTopicAliasRepository.search_by_alias` build; this two-step
approach is correct for a first page's *presence* of both kinds of
match, the pragmatic scope for a first implementation of this feature.
"""

from app.modules.medical_topics.application.dto import SearchTopicsInput, SearchTopicsOutput
from app.modules.medical_topics.application.services._summary_mappers import topic_to_summary
from app.modules.medical_topics.domain.enums import TopicStatus, TopicVisibility
from app.modules.medical_topics.domain.repositories import (
    MedicalTopicAliasRepository,
    MedicalTopicRepository,
)

_PUBLISHED = (TopicStatus.PUBLISHED,)
_PUBLIC = (TopicVisibility.PUBLIC,)


class SearchTopicsService:
    def __init__(
        self,
        *,
        topic_repository: MedicalTopicRepository,
        alias_repository: MedicalTopicAliasRepository,
    ) -> None:
        self._topics = topic_repository
        self._aliases = alias_repository

    async def search(self, input_dto: SearchTopicsInput) -> SearchTopicsOutput:
        topics, total = await self._topics.search(
            query=input_dto.query,
            status=_PUBLISHED,
            visibility=_PUBLIC,
            specialty_id=input_dto.specialty_id,
            offset=input_dto.offset,
            limit=input_dto.limit,
        )
        matched_ids = {t.id for t in topics}

        remaining = input_dto.limit - len(topics)
        if remaining > 0:
            alias_matches, alias_total = await self._aliases.search_by_alias(
                input_dto.query, limit=remaining + len(matched_ids)
            )
            alias_topic_ids = [
                a.topic_id.value for a in alias_matches if a.topic_id.value not in matched_ids
            ]
            if alias_topic_ids:
                extra_topics = await self._topics.list_by_ids(alias_topic_ids)
                extra_topics = [
                    t
                    for t in extra_topics
                    if t.status is TopicStatus.PUBLISHED
                    and t.visibility is TopicVisibility.PUBLIC
                    and (input_dto.specialty_id is None or t.specialty_id == input_dto.specialty_id)
                ][:remaining]
                topics = list(topics) + extra_topics
                total += min(len(extra_topics), alias_total)

        return SearchTopicsOutput(items=tuple(topic_to_summary(t) for t in topics), total=total)

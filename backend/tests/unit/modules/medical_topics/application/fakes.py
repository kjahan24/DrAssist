"""In-memory test doubles for the Medical Topics module's repositories
and Unit of Work — each implements the exact same interface its real
SQLAlchemy counterpart does, per
`docs/backend-architecture/12_testing_architecture.md` ("fakes over mocks
as the default"). Application-layer service tests depend on these, never
on a real database.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.modules.medical_topics.domain.entities import (
    MedicalTopic,
    MedicalTopicAlias,
    MedicalTopicFollower,
    MedicalTopicRelation,
    TopicSpecialty,
)
from app.modules.medical_topics.domain.enums import TopicStatus, TopicVisibility
from app.modules.medical_topics.domain.repositories import (
    MedicalTopicAliasRepository,
    MedicalTopicFollowerRepository,
    MedicalTopicRelationRepository,
    MedicalTopicRepository,
    TopicSpecialtyRepository,
)
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent


class FakeMedicalTopicRepository(MedicalTopicRepository):
    def __init__(self) -> None:
        self._topics: dict[UUID, MedicalTopic] = {}

    async def get_by_id(self, topic_id: UUID) -> MedicalTopic | None:
        return self._topics.get(topic_id)

    async def get_by_slug(self, slug: str) -> MedicalTopic | None:
        normalized = slug.strip().lower()
        for topic in self._topics.values():
            if str(topic.slug) == normalized:
                return topic
        return None

    async def list_children(
        self, parent_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[MedicalTopic]:
        matches = [t for t in self._topics.values() if t.parent_id == parent_id]
        return matches[offset : offset + limit]

    async def search(
        self,
        *,
        query: str | None = None,
        status: Sequence[TopicStatus] | None = None,
        visibility: Sequence[TopicVisibility] | None = None,
        specialty_id: UUID | None = None,
        parent_id: UUID | None = None,
        featured_only: bool = False,
        include_deleted: bool = False,
        sort_by: str = "created_at",
        sort_order: Literal["asc", "desc"] = "asc",
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[MedicalTopic], int]:
        matches = list(self._topics.values())
        if status:
            matches = [t for t in matches if t.status in status]
        if visibility:
            matches = [t for t in matches if t.visibility in visibility]
        if specialty_id is not None:
            matches = [t for t in matches if t.specialty_id == specialty_id]
        if parent_id is not None:
            matches = [t for t in matches if t.parent_id == parent_id]
        if featured_only:
            matches = [t for t in matches if t.is_featured]
        if query:
            term = query.strip().lower()
            matches = [
                t
                for t in matches
                if term in str(t.name).lower()
                or (t.description is not None and term in str(t.description).lower())
            ]
        matches.sort(key=lambda t: self._sort_key(t, sort_by), reverse=sort_order == "desc")
        total = len(matches)
        return matches[offset : offset + limit], total

    @staticmethod
    def _sort_key(topic: MedicalTopic, sort_by: str) -> str | float | datetime:
        if sort_by in ("trending_score", "popularity_score"):
            value: float = getattr(topic, sort_by)
            return value
        if sort_by == "name":
            return str(topic.name)
        timestamp: datetime = getattr(topic, sort_by, topic.created_at)
        return timestamp if isinstance(timestamp, datetime) else topic.created_at

    async def list_by_ids(self, topic_ids: Sequence[UUID]) -> list[MedicalTopic]:
        return [self._topics[tid] for tid in topic_ids if tid in self._topics]

    async def add(self, topic: MedicalTopic) -> None:
        self._topics[topic.id] = topic

    async def remove(self, topic_id: UUID) -> None:
        self._topics.pop(topic_id, None)


class FakeTopicSpecialtyRepository(TopicSpecialtyRepository):
    def __init__(self) -> None:
        self._specialties: dict[UUID, TopicSpecialty] = {}

    async def get_by_id(self, specialty_id: UUID) -> TopicSpecialty | None:
        return self._specialties.get(specialty_id)

    async def get_by_slug(self, slug: str) -> TopicSpecialty | None:
        for specialty in self._specialties.values():
            if str(specialty.slug) == slug:
                return specialty
        return None

    async def get_by_name(self, name: str) -> TopicSpecialty | None:
        for specialty in self._specialties.values():
            if str(specialty.name) == name:
                return specialty
        return None

    async def list_active(self, *, offset: int = 0, limit: int = 100) -> list[TopicSpecialty]:
        matches = [s for s in self._specialties.values() if s.is_active]
        return matches[offset : offset + limit]

    async def add(self, specialty: TopicSpecialty) -> None:
        self._specialties[specialty.id] = specialty


class FakeMedicalTopicFollowerRepository(MedicalTopicFollowerRepository):
    def __init__(self) -> None:
        self._followers: dict[UUID, MedicalTopicFollower] = {}

    async def get_by_topic_and_user(
        self, topic_id: UUID, user_id: UUID
    ) -> MedicalTopicFollower | None:
        for follower in self._followers.values():
            if follower.topic_id.value == topic_id and follower.user_id == user_id:
                return follower
        return None

    async def list_by_topic(
        self, topic_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[MedicalTopicFollower]:
        matches = [f for f in self._followers.values() if f.topic_id.value == topic_id]
        return matches[offset : offset + limit]

    async def list_by_user(
        self, user_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[MedicalTopicFollower]:
        matches = [f for f in self._followers.values() if f.user_id == user_id]
        return matches[offset : offset + limit]

    async def count_by_topic(self, topic_id: UUID) -> int:
        return sum(1 for f in self._followers.values() if f.topic_id.value == topic_id)

    async def add(self, follower: MedicalTopicFollower) -> None:
        self._followers[follower.id] = follower

    async def remove(self, topic_id: UUID, user_id: UUID) -> None:
        match_id = next(
            (
                fid
                for fid, f in self._followers.items()
                if f.topic_id.value == topic_id and f.user_id == user_id
            ),
            None,
        )
        if match_id is not None:
            del self._followers[match_id]


class FakeMedicalTopicAliasRepository(MedicalTopicAliasRepository):
    def __init__(self) -> None:
        self._aliases: dict[UUID, MedicalTopicAlias] = {}

    async def get_by_id(self, alias_id: UUID) -> MedicalTopicAlias | None:
        return self._aliases.get(alias_id)

    async def list_by_topic(self, topic_id: UUID) -> list[MedicalTopicAlias]:
        return [a for a in self._aliases.values() if a.topic_id.value == topic_id]

    async def search_by_alias(
        self, term: str, *, offset: int = 0, limit: int = 20
    ) -> tuple[Sequence[MedicalTopicAlias], int]:
        normalized = term.strip().lower()
        matches = [a for a in self._aliases.values() if normalized in str(a.alias)]
        total = len(matches)
        return matches[offset : offset + limit], total

    async def add(self, alias: MedicalTopicAlias) -> None:
        self._aliases[alias.id] = alias

    async def remove(self, alias_id: UUID) -> None:
        self._aliases.pop(alias_id, None)


class FakeMedicalTopicRelationRepository(MedicalTopicRelationRepository):
    def __init__(self) -> None:
        self._relations: dict[UUID, MedicalTopicRelation] = {}

    async def get_by_id(self, relation_id: UUID) -> MedicalTopicRelation | None:
        return self._relations.get(relation_id)

    async def list_related(self, topic_id: UUID) -> list[MedicalTopicRelation]:
        return [
            r
            for r in self._relations.values()
            if r.topic_id.value == topic_id or r.related_topic_id == topic_id
        ]

    async def exists(self, topic_id: UUID, related_topic_id: UUID) -> bool:
        return any(
            (r.topic_id.value == topic_id and r.related_topic_id == related_topic_id)
            or (r.topic_id.value == related_topic_id and r.related_topic_id == topic_id)
            for r in self._relations.values()
        )

    async def add(self, relation: MedicalTopicRelation) -> None:
        self._relations[relation.id] = relation

    async def remove(self, relation_id: UUID) -> None:
        self._relations.pop(relation_id, None)


class FakeUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.committed = False
        self.rolled_back = False
        self.published_events: list[DomainEvent] = []
        self._pending_events: list[DomainEvent] = []

    def collect_events(self, events: list[DomainEvent]) -> None:
        self._pending_events.extend(events)

    async def commit(self) -> None:
        self.committed = True
        self.published_events.extend(self._pending_events)
        self._pending_events = []

    async def rollback(self) -> None:
        self.rolled_back = True
        self._pending_events = []

    async def flush(self) -> None:
        pass

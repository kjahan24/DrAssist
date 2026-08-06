"""Medical Topics module aggregate roots: MedicalTopic,
MedicalTopicFollower, MedicalTopicAlias, MedicalTopicRelation,
TopicSpecialty.

Each is its own aggregate — every reference to another aggregate is by ID
only (`TopicId`/`UUID`), never by object reference, the same rule
`app.modules.community.domain.entities` already follows for itself. All
mutation goes through named methods that enforce the aggregate's own
invariants and record domain events; nothing here performs I/O.

`TopicSpecialty` mirrors `app.modules.community.domain.entities
.CommunityCategory` exactly — a platform-wide, admin-manageable
vocabulary entry (Cardiology, Dermatology, ...) modeled as a real table
rather than a closed `StrEnum`, per this task's own "Architecture must be
extensible" requirement for specialties.

`MedicalTopicAlias` deliberately covers both this task's "Topic aliases"
and "Topic synonyms" FEATURES bullets with one entity: both are,
structurally, just "an alternate name for a topic used to widen search
matching" — the DOMAIN section names only one entity
(`MedicalTopicAlias`), not two, so a single unified alternate-name
mechanism satisfies both bullets rather than inventing an unrequested
second, near-identical entity.
"""

from dataclasses import dataclass
from uuid import UUID

from app.modules.medical_topics.domain.enums import (
    TopicRelationType,
    TopicStatus,
    TopicVisibility,
)
from app.modules.medical_topics.domain.events import (
    MedicalTopicAliasCreated,
    MedicalTopicCreated,
    MedicalTopicFeaturedChanged,
    MedicalTopicRelationCreated,
    MedicalTopicUpdated,
    TopicFollowed,
    TopicSpecialtyCreated,
)
from app.modules.medical_topics.domain.exceptions import (
    NegativeTopicScoreError,
    TopicCannotBeOwnParentError,
    TopicCannotRelateToItselfError,
)
from app.modules.medical_topics.domain.value_objects import (
    TopicColor,
    TopicDescription,
    TopicId,
    TopicName,
    TopicSlug,
)
from app.shared.domain.entity import AggregateRoot


@dataclass(kw_only=True, eq=False)
class MedicalTopic(AggregateRoot):
    slug: TopicSlug
    name: TopicName
    description: TopicDescription | None = None
    icon: str | None = None
    color: TopicColor | None = None
    parent_id: UUID | None = None
    specialty_id: UUID | None = None
    status: TopicStatus = TopicStatus.DRAFT
    visibility: TopicVisibility = TopicVisibility.PUBLIC
    is_featured: bool = False
    trending_score: float = 0.0
    popularity_score: float = 0.0
    created_by: UUID | None = None
    updated_by: UUID | None = None

    @classmethod
    def create(
        cls,
        *,
        slug: TopicSlug,
        name: TopicName,
        description: TopicDescription | None = None,
        icon: str | None = None,
        color: TopicColor | None = None,
        parent_id: UUID | None = None,
        specialty_id: UUID | None = None,
        visibility: TopicVisibility = TopicVisibility.PUBLIC,
        created_by: UUID | None = None,
    ) -> "MedicalTopic":
        topic = cls(
            slug=slug,
            name=name,
            description=description,
            icon=icon,
            color=color,
            parent_id=parent_id,
            specialty_id=specialty_id,
            visibility=visibility,
            created_by=created_by,
            updated_by=created_by,
        )
        topic.record_event(MedicalTopicCreated(topic_id=topic.id, slug=str(slug), name=str(name)))
        return topic

    def update_profile(
        self,
        *,
        name: TopicName | None = None,
        description: TopicDescription | None = None,
        clear_description: bool = False,
        icon: str | None = None,
        clear_icon: bool = False,
        color: TopicColor | None = None,
        clear_color: bool = False,
        status: TopicStatus | None = None,
        visibility: TopicVisibility | None = None,
        parent_id: UUID | None = None,
        clear_parent: bool = False,
        specialty_id: UUID | None = None,
        clear_specialty: bool = False,
        updated_by: UUID | None = None,
    ) -> None:
        """`clear_description=True`/`clear_icon=True`/`clear_color=True`/
        `clear_parent=True`/`clear_specialty=True` are how a caller
        removes an existing optional field (distinct from passing the
        corresponding field as `None`, which just means "no change") —
        the same clearing-sentinel shape
        `app.modules.community.domain.entities.Community.update_profile`
        already establishes.

        Cycle detection for `parent_id` is deliberately NOT done here: it
        requires walking the full ancestor chain via repository lookups,
        a cross-aggregate concern this pure entity method has no access
        to — `UpdateTopicService` performs that check before calling this
        method (see that service's own docstring). Only the local,
        single-aggregate invariant ("a topic is not its own parent") is
        enforced here.
        """
        if parent_id is not None and parent_id == self.id:
            raise TopicCannotBeOwnParentError(self.id)

        if name is not None:
            self.name = name
        if clear_description:
            self.description = None
        elif description is not None:
            self.description = description
        if clear_icon:
            self.icon = None
        elif icon is not None:
            self.icon = icon
        if clear_color:
            self.color = None
        elif color is not None:
            self.color = color
        if status is not None:
            self.status = status
        if visibility is not None:
            self.visibility = visibility
        if clear_parent:
            self.parent_id = None
        elif parent_id is not None:
            self.parent_id = parent_id
        if clear_specialty:
            self.specialty_id = None
        elif specialty_id is not None:
            self.specialty_id = specialty_id
        if updated_by is not None:
            self.updated_by = updated_by

        self.touch()
        self.record_event(MedicalTopicUpdated(topic_id=self.id))

    def set_featured(self, value: bool) -> None:
        """Platform-level curation flag — set by a caller holding the
        `topics.feature` RBAC permission, not tied to any per-resource
        ownership (this module has none — see `MedicalTopicRepository`'s
        own docstring), the same authorization split
        `app.modules.community.application.services
        .feature_communities_service.FeatureCommunitiesService`
        establishes for `Community.set_featured`."""
        if self.is_featured is value:
            return
        self.is_featured = value
        self.touch()
        self.record_event(MedicalTopicFeaturedChanged(topic_id=self.id, is_featured=value))

    def update_trending_score(self, value: float) -> None:
        if value < 0:
            raise NegativeTopicScoreError("trending_score")
        self.trending_score = value
        self.touch()

    def update_popularity_score(self, value: float) -> None:
        if value < 0:
            raise NegativeTopicScoreError("popularity_score")
        self.popularity_score = value
        self.touch()


@dataclass(kw_only=True, eq=False)
class MedicalTopicFollower(AggregateRoot):
    topic_id: TopicId
    user_id: UUID

    @classmethod
    def create(cls, *, topic_id: TopicId, user_id: UUID) -> "MedicalTopicFollower":
        follower = cls(topic_id=topic_id, user_id=user_id)
        follower.record_event(TopicFollowed(topic_id=topic_id.value, user_id=user_id))
        return follower


@dataclass(kw_only=True, eq=False)
class MedicalTopicAlias(AggregateRoot):
    topic_id: TopicId
    alias: TopicName

    @classmethod
    def create(cls, *, topic_id: TopicId, alias: TopicName) -> "MedicalTopicAlias":
        entity = cls(topic_id=topic_id, alias=alias)
        entity.record_event(
            MedicalTopicAliasCreated(alias_id=entity.id, topic_id=topic_id.value, alias=str(alias))
        )
        return entity


@dataclass(kw_only=True, eq=False)
class MedicalTopicRelation(AggregateRoot):
    topic_id: TopicId
    related_topic_id: UUID
    relation_type: TopicRelationType = TopicRelationType.RELATED

    @classmethod
    def create(
        cls,
        *,
        topic_id: TopicId,
        related_topic_id: UUID,
        relation_type: TopicRelationType = TopicRelationType.RELATED,
    ) -> "MedicalTopicRelation":
        if topic_id.value == related_topic_id:
            raise TopicCannotRelateToItselfError(topic_id.value)
        relation = cls(
            topic_id=topic_id, related_topic_id=related_topic_id, relation_type=relation_type
        )
        relation.record_event(
            MedicalTopicRelationCreated(
                relation_id=relation.id,
                topic_id=topic_id.value,
                related_topic_id=related_topic_id,
            )
        )
        return relation


@dataclass(kw_only=True, eq=False)
class TopicSpecialty(AggregateRoot):
    """A platform-wide, admin-manageable vocabulary entry (Cardiology,
    Dermatology, ...) — see this module's own docstring for why it's a
    real table rather than a closed `StrEnum`."""

    name: TopicName
    slug: TopicSlug
    description: TopicDescription | None = None
    is_active: bool = True

    @classmethod
    def create(
        cls,
        *,
        name: TopicName,
        slug: TopicSlug,
        description: TopicDescription | None = None,
    ) -> "TopicSpecialty":
        specialty = cls(name=name, slug=slug, description=description)
        specialty.record_event(TopicSpecialtyCreated(specialty_id=specialty.id, name=str(name)))
        return specialty

    def deactivate(self) -> None:
        self.is_active = False
        self.touch()

    def activate(self) -> None:
        self.is_active = True
        self.touch()

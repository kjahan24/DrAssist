"""Data Transfer Objects for the Medical Topics module's application
layer.

Distinct from both domain entities (never leave the module) and API
schemas (`presentation/schemas.py`, the Pydantic v2 validation boundary).
Use-case input/output DTOs are plain, immutable dataclasses — the same
shape `app.modules.community.application.dto` already establishes;
`TopicSummaryDTO` is also re-exported from `public/dto.py` for other
modules to depend on.
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from app.modules.medical_topics.domain.enums import TopicStatus, TopicVisibility

# --- CreateTopic -------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CreateTopicInput:
    slug: str
    name: str
    created_by: UUID | None = None
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    parent_id: UUID | None = None
    specialty_id: UUID | None = None
    visibility: TopicVisibility = TopicVisibility.PUBLIC


@dataclass(frozen=True, slots=True)
class CreateTopicOutput:
    topic_id: UUID
    slug: str
    name: str
    status: TopicStatus
    visibility: TopicVisibility


# --- UpdateTopic ---------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class UpdateTopicInput:
    topic_id: UUID
    updated_by: UUID | None = None
    name: str | None = None
    description: str | None = None
    clear_description: bool = False
    icon: str | None = None
    clear_icon: bool = False
    color: str | None = None
    clear_color: bool = False
    status: TopicStatus | None = None
    visibility: TopicVisibility | None = None
    parent_id: UUID | None = None
    clear_parent: bool = False
    specialty_id: UUID | None = None
    clear_specialty: bool = False


@dataclass(frozen=True, slots=True)
class UpdateTopicOutput:
    topic_id: UUID
    name: str
    status: TopicStatus
    visibility: TopicVisibility


# --- DeleteTopic ---------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DeleteTopicInput:
    topic_id: UUID


# --- FollowTopic / UnfollowTopic ------------------------------------------------


@dataclass(frozen=True, slots=True)
class FollowTopicInput:
    topic_id: UUID
    user_id: UUID


@dataclass(frozen=True, slots=True)
class FollowTopicOutput:
    follower_id: UUID
    topic_id: UUID
    user_id: UUID
    followed_at: datetime


@dataclass(frozen=True, slots=True)
class UnfollowTopicInput:
    topic_id: UUID
    user_id: UUID


# --- Cross-cutting read models (also re-exported via public/dto.py) ------------


@dataclass(frozen=True, slots=True)
class TopicSummaryDTO:
    topic_id: UUID
    slug: str
    name: str
    status: TopicStatus
    visibility: TopicVisibility
    created_at: datetime
    updated_at: datetime
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    parent_id: UUID | None = None
    specialty_id: UUID | None = None
    is_featured: bool = False
    trending_score: float = 0.0
    popularity_score: float = 0.0
    created_by: UUID | None = None

    @property
    def id(self) -> UUID:
        """Alias for `topic_id` — see `AppointmentSummaryDTO.id`'s own
        docstring in `app.modules.appointment.application.dto` for the
        full reasoning (identical situation in every module)."""
        return self.topic_id


@dataclass(frozen=True, slots=True)
class TopicFollowerSummaryDTO:
    follower_id: UUID
    topic_id: UUID
    user_id: UUID
    followed_at: datetime

    @property
    def id(self) -> UUID:
        return self.follower_id


# --- ListTopics ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ListTopicsInput:
    query: str | None = None
    status: tuple[TopicStatus, ...] | None = None
    visibility: tuple[TopicVisibility, ...] | None = None
    specialty_id: UUID | None = None
    parent_id: UUID | None = None
    include_deleted: bool = False
    sort_by: str = "created_at"
    sort_order: str = "asc"
    offset: int = 0
    limit: int = 20


@dataclass(frozen=True, slots=True)
class ListTopicsOutput:
    items: tuple[TopicSummaryDTO, ...]
    total: int


# --- SearchTopics ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SearchTopicsInput:
    query: str
    specialty_id: UUID | None = None
    offset: int = 0
    limit: int = 20


@dataclass(frozen=True, slots=True)
class SearchTopicsOutput:
    items: tuple[TopicSummaryDTO, ...]
    total: int


# --- TrendingTopics ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TrendingTopicsInput:
    specialty_id: UUID | None = None
    offset: int = 0
    limit: int = 20


# --- FeaturedTopics (also platform-level curation toggle) ----------------------------


@dataclass(frozen=True, slots=True)
class FeaturedTopicsInput:
    offset: int = 0
    limit: int = 20


@dataclass(frozen=True, slots=True)
class SetTopicFeaturedInput:
    topic_id: UUID
    featured: bool


# --- RelatedTopics ---------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RelatedTopicsInput:
    topic_id: UUID
    limit: int = 20


# --- Topic specialties -------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TopicSpecialtySummaryDTO:
    specialty_id: UUID
    name: str
    slug: str
    is_active: bool
    description: str | None = None

    @property
    def id(self) -> UUID:
        return self.specialty_id


@dataclass(frozen=True, slots=True)
class CreateTopicSpecialtyInput:
    name: str
    slug: str
    description: str | None = None


@dataclass(frozen=True, slots=True)
class CreateTopicSpecialtyOutput:
    specialty_id: UUID
    name: str
    slug: str


# --- Topic aliases / synonyms ---------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TopicAliasSummaryDTO:
    alias_id: UUID
    topic_id: UUID
    alias: str

    @property
    def id(self) -> UUID:
        return self.alias_id


@dataclass(frozen=True, slots=True)
class CreateTopicAliasInput:
    topic_id: UUID
    alias: str


@dataclass(frozen=True, slots=True)
class DeleteTopicAliasInput:
    alias_id: UUID


# --- Topic relations ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TopicRelationSummaryDTO:
    relation_id: UUID
    topic_id: UUID
    related_topic_id: UUID
    relation_type: str

    @property
    def id(self) -> UUID:
        return self.relation_id


@dataclass(frozen=True, slots=True)
class CreateTopicRelationInput:
    topic_id: UUID
    related_topic_id: UUID
    relation_type: str = "related"


@dataclass(frozen=True, slots=True)
class DeleteTopicRelationInput:
    relation_id: UUID


@dataclass(frozen=True, slots=True)
class RelatedTopicsOutput:
    items: tuple[TopicSummaryDTO, ...] = field(default_factory=tuple)

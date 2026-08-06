"""Enums owned by the Community Posts module's domain."""

from enum import StrEnum


class PostType(StrEnum):
    """What kind of content a post is — purely descriptive/filterable
    (this task's own "Type" search filter), no type-specific validation
    or workflow branches on it anywhere in this module."""

    DISCUSSION = "discussion"
    EXPERIENCE = "experience"
    CLINICAL_CASE = "clinical_case"
    MEDICAL_NEWS = "medical_news"
    RESEARCH = "research"
    EDUCATIONAL = "educational"
    CLINICAL_PEARL = "clinical_pearl"
    ANNOUNCEMENT = "announcement"


class PostStatus(StrEnum):
    """A post's content lifecycle — the same `DRAFT -> PUBLISHED ->
    ARCHIVED` shape `app.modules.medical_topics.domain.enums.TopicStatus`
    already establishes for itself, here mapping directly onto this
    task's own "Draft"/"Publish"/"Archive" FEATURES bullets."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class PostVisibility(StrEnum):
    """Who may view a published post, independent of the parent
    community's own `CommunityVisibility` — a public community can still
    contain individually restricted posts. `PUBLIC` is visible to anyone
    who can see the community at all; `MEMBERS_ONLY` requires active
    community membership (checked via `CommunityQueryPort
    .is_active_member`); `PRIVATE` is visible only to the author and
    community moderators/admins — the same three-tier shape
    `CommunityVisibility` (`PUBLIC`/`VERIFIED_ONLY`/`PRIVATE`) already
    establishes, renamed here to fit a single post's own audience rather
    than a whole community's."""

    PUBLIC = "public"
    MEMBERS_ONLY = "members_only"
    PRIVATE = "private"

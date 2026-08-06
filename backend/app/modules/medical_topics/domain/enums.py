"""Enums owned by the Medical Topics module's domain."""

from enum import StrEnum


class TopicStatus(StrEnum):
    """A topic's content lifecycle — independent of `TopicVisibility`
    (audience/discoverability). `DRAFT` topics are still being authored;
    `PUBLISHED` topics are complete and eligible for discovery surfaces
    (search/browse/trending/featured, subject to `TopicVisibility` too —
    see that enum's own docstring); `ARCHIVED` topics are retired from
    discovery but remain resolvable by id/slug so existing
    Community/Post/Question/Answer references never break."""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class TopicVisibility(StrEnum):
    """Who may discover a topic — this module is platform-wide (not
    organization-scoped, the same "reusable, shared vocabulary" shape
    `app.modules.community.domain.entities.CommunityCategory`/
    `CommunityTag` already establishes for themselves), so `PRIVATE` here
    means "hidden from every caller's public-facing surfaces platform-
    wide," not "scoped to one tenant." `PUBLIC` topics appear in
    search/browse/trending/featured; `UNLISTED` topics are resolvable via
    a direct id/slug (e.g. a Community/Post already links to one) but
    excluded from those discovery listings; `PRIVATE` topics are hidden
    everywhere, for staff-curated topics not yet ready for any audience."""

    PUBLIC = "public"
    UNLISTED = "unlisted"
    PRIVATE = "private"


class TopicRelationType(StrEnum):
    """The nature of an edge in the "Related Topics" graph — distinct
    from parent/child hierarchy (`MedicalTopic.parent_id`), which encodes
    taxonomic placement, not general association. `RELATED` is a plain,
    symmetric association (the default "related topics" case); `SEE_ALSO`
    is an editorial cross-reference (e.g. "for dosing see X"), the same
    "related vs. editorial cross-reference" split reference taxonomies
    (e.g. Wikipedia's own "See also" sections) already draw."""

    RELATED = "related"
    SEE_ALSO = "see_also"

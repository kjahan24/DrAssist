"""Value objects specific to the Community Posts module.

`PostId` mirrors `app.modules.medical_topics.domain.value_objects
.TopicId`/`app.modules.community.domain.value_objects.CommunityId`
exactly — a strongly-typed wrapper used only as the cross-aggregate
*reference* field (`CommunityPostTopic.post_id`, `CommunityPostTag
.post_id`, `CommunityPostAttachment.post_id`), never as `CommunityPost.id`
itself (which stays a plain `UUID`, like every other aggregate root).

`PostSlug.from_title`/`PostExcerpt.from_body` implement this task's own
"Slug generation"/"Excerpt generation" FEATURES bullets as pure,
I/O-free transforms co-located with the value object that owns their
validation — `PostSlug.from_title` falls back to a short random suffix
(via `uuid4()`, not real I/O — the same non-deterministic-but-pure
randomness `app.shared.domain.entity.Entity.id`'s own `default_factory`
already uses) when a title slugifies to something shorter than the
minimum length (e.g. a title made entirely of punctuation/emoji), so
`PostSlug.from_title` can never itself fail validation. Uniqueness
*within a community* (a repository-level concern) is handled by
`CreatePostService`, not here — see that service's own docstring.
"""

import re
from dataclasses import dataclass
from uuid import UUID, uuid4

from app.modules.community_posts.domain.exceptions import (
    InvalidPostSlugError,
    PostBodyRequiredError,
    PostExcerptRequiredError,
    PostExcerptTooLongError,
    PostTitleRequiredError,
    PostTitleTooLongError,
)
from app.shared.domain.value_object import ValueObject

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SLUG_MIN_LENGTH = 3
_SLUG_MAX_LENGTH = 100
_TITLE_MAX_LENGTH = 300
_EXCERPT_MAX_LENGTH = 500
_EXCERPT_GENERATED_LENGTH = 200

_SLUGIFY_STRIP_RE = re.compile(r"[^a-z0-9\s-]")
_SLUGIFY_HYPHENATE_RE = re.compile(r"[\s-]+")
_MARKDOWN_STRIP_RE = re.compile(r"[#*_`>\[\]!]")
_WHITESPACE_RE = re.compile(r"\s+")


def _slugify(text: str) -> str:
    lowered = text.strip().lower()
    stripped = _SLUGIFY_STRIP_RE.sub("", lowered)
    return _SLUGIFY_HYPHENATE_RE.sub("-", stripped).strip("-")


@dataclass(frozen=True, slots=True)
class PostId(ValueObject):
    value: UUID

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class PostSlug(ValueObject):
    """A URL-safe identifier, unique within one community (not
    platform-wide — see `CommunityPost`'s own docstring for why slug
    uniqueness is scoped to `(community_id, slug)`, the same scoping
    `CommunitySlug` uses for `(organization_id, slug)`)."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not (_SLUG_MIN_LENGTH <= len(normalized) <= _SLUG_MAX_LENGTH) or not _SLUG_PATTERN.match(
            normalized
        ):
            raise InvalidPostSlugError(self.value)
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_title(cls, title: str) -> "PostSlug":
        slug = _slugify(title)
        if len(slug) < _SLUG_MIN_LENGTH:
            suffix = uuid4().hex[:8]
            slug = f"{slug}-{suffix}" if slug else f"post-{suffix}"
        if len(slug) > _SLUG_MAX_LENGTH:
            slug = slug[:_SLUG_MAX_LENGTH].rstrip("-")
        return cls(slug)


@dataclass(frozen=True, slots=True)
class PostTitle(ValueObject):
    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise PostTitleRequiredError()
        if len(stripped) > _TITLE_MAX_LENGTH:
            raise PostTitleTooLongError(_TITLE_MAX_LENGTH)
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class PostExcerpt(ValueObject):
    """Optional short summary — `CommunityPost.excerpt` is `PostExcerpt |
    None`, never an empty-string `PostExcerpt`; a caller with nothing to
    say passes `None`, not a blank excerpt (the same rule
    `CommunityDescription`/`TopicDescription` already follow) — in that
    case `CommunityPost.create`/`update_content` calls `from_body`
    instead."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise PostExcerptRequiredError()
        if len(stripped) > _EXCERPT_MAX_LENGTH:
            raise PostExcerptTooLongError(_EXCERPT_MAX_LENGTH)
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_body(cls, body: str) -> "PostExcerpt":
        if not body.strip():
            raise PostBodyRequiredError()
        plain = _MARKDOWN_STRIP_RE.sub("", body)
        plain = _WHITESPACE_RE.sub(" ", plain).strip()
        if len(plain) <= _EXCERPT_GENERATED_LENGTH:
            return cls(plain)
        truncated = plain[:_EXCERPT_GENERATED_LENGTH].rsplit(" ", 1)[0].rstrip(".,;:!?")
        return cls(f"{truncated}...")

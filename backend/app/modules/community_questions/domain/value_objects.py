"""Value objects specific to the Community Questions module.

`QuestionId` mirrors `app.modules.community_posts.domain.value_objects
.PostId` exactly — a strongly-typed wrapper used only as the
cross-aggregate *reference* field (`CommunityQuestionTopic.question_id`,
`CommunityQuestionTag.question_id`, `CommunityQuestionAttachment
.question_id`, `CommunityQuestionFollower.question_id`), never as
`CommunityQuestion.id` itself (which stays a plain `UUID`, like every
other aggregate root).

`QuestionSlug.from_title`/`QuestionSummary.from_body` mirror `PostSlug
.from_title`/`PostExcerpt.from_body` exactly — pure, I/O-free transforms
co-located with the value object that owns their validation. Uniqueness
*within a community* (a repository-level concern) is handled by
`CreateQuestionService`, not here — see that service's own docstring.
"""

import re
from dataclasses import dataclass
from uuid import UUID, uuid4

from app.modules.community_questions.domain.exceptions import (
    InvalidQuestionSlugError,
    QuestionBodyRequiredError,
    QuestionSummaryRequiredError,
    QuestionSummaryTooLongError,
    QuestionTitleRequiredError,
    QuestionTitleTooLongError,
)
from app.shared.domain.value_object import ValueObject

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_SLUG_MIN_LENGTH = 3
_SLUG_MAX_LENGTH = 100
_TITLE_MAX_LENGTH = 300
_SUMMARY_MAX_LENGTH = 500
_SUMMARY_GENERATED_LENGTH = 200

_SLUGIFY_STRIP_RE = re.compile(r"[^a-z0-9\s-]")
_SLUGIFY_HYPHENATE_RE = re.compile(r"[\s-]+")
_MARKDOWN_STRIP_RE = re.compile(r"[#*_`>\[\]!]")
_WHITESPACE_RE = re.compile(r"\s+")


def _slugify(text: str) -> str:
    lowered = text.strip().lower()
    stripped = _SLUGIFY_STRIP_RE.sub("", lowered)
    return _SLUGIFY_HYPHENATE_RE.sub("-", stripped).strip("-")


@dataclass(frozen=True, slots=True)
class QuestionId(ValueObject):
    value: UUID

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class QuestionSlug(ValueObject):
    """A URL-safe identifier, unique within one community (not
    platform-wide) — the same `(community_id, slug)` scoping `PostSlug`
    already establishes for itself."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not (_SLUG_MIN_LENGTH <= len(normalized) <= _SLUG_MAX_LENGTH) or not _SLUG_PATTERN.match(
            normalized
        ):
            raise InvalidQuestionSlugError(self.value)
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_title(cls, title: str) -> "QuestionSlug":
        slug = _slugify(title)
        if len(slug) < _SLUG_MIN_LENGTH:
            suffix = uuid4().hex[:8]
            slug = f"{slug}-{suffix}" if slug else f"question-{suffix}"
        if len(slug) > _SLUG_MAX_LENGTH:
            slug = slug[:_SLUG_MAX_LENGTH].rstrip("-")
        return cls(slug)


@dataclass(frozen=True, slots=True)
class QuestionTitle(ValueObject):
    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise QuestionTitleRequiredError()
        if len(stripped) > _TITLE_MAX_LENGTH:
            raise QuestionTitleTooLongError(_TITLE_MAX_LENGTH)
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class QuestionSummary(ValueObject):
    """A short summary of the question body — always populated (either
    caller-supplied or auto-derived via `from_body`), the same
    non-optional-on-the-entity shape `CommunityQuestion.summary`
    establishes for itself (unlike `PostExcerpt`, which stays optional at
    the entity level in `community_posts`; here `CommunityQuestion.create`
    always resolves one before construction, see that method's own
    docstring)."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise QuestionSummaryRequiredError()
        if len(stripped) > _SUMMARY_MAX_LENGTH:
            raise QuestionSummaryTooLongError(_SUMMARY_MAX_LENGTH)
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_body(cls, body: str) -> "QuestionSummary":
        if not body.strip():
            raise QuestionBodyRequiredError()
        plain = _MARKDOWN_STRIP_RE.sub("", body)
        plain = _WHITESPACE_RE.sub(" ", plain).strip()
        if len(plain) <= _SUMMARY_GENERATED_LENGTH:
            return cls(plain)
        truncated = plain[:_SUMMARY_GENERATED_LENGTH].rsplit(" ", 1)[0].rstrip(".,;:!?")
        return cls(f"{truncated}...")

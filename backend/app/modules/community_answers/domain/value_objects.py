"""Value objects specific to the Community Answers module.

`AnswerId` mirrors `app.modules.community_questions.domain.value_objects
.QuestionId` exactly — a strongly-typed wrapper used only as the
cross-aggregate *reference* field (`CommunityAnswerRevision.answer_id`,
`CommunityAnswerAttachment.answer_id`), never as `CommunityAnswer.id`
itself (which stays a plain `UUID`, like every other aggregate root).

Unlike `app.modules.community_posts.domain.value_objects.PostSlug`/
`app.modules.community_questions.domain.value_objects.QuestionSlug`, this
module has no slug value object — this task's own DOMAIN VALUE OBJECTS
list names only `AnswerId`/`AnswerBody`/`AnswerSummary`, no
`AnswerSlug`/`AnswerTitle`; an answer is addressed purely by its `UUID`
id, not a human-readable per-question URL segment, since it has no
independent title of its own to slugify.

`AnswerBody` is itself a value object here (unlike `CommunityPost.body`/
`CommunityQuestion.body`, which stayed plain `str` in those two modules)
— this task's own DOMAIN VALUE OBJECTS list names `AnswerBody`
explicitly, so this module honors that literally rather than reusing the
"body stays a plain string" precedent.

`AnswerSummary.from_body` mirrors `QuestionSummary.from_body`/
`PostExcerpt.from_body` exactly — a pure, I/O-free transform co-located
with the value object that owns its validation.
"""

import re
from dataclasses import dataclass
from uuid import UUID

from app.modules.community_answers.domain.exceptions import (
    AnswerBodyRequiredError,
    AnswerBodyTooLongError,
    AnswerSummaryRequiredError,
    AnswerSummaryTooLongError,
)
from app.shared.domain.value_object import ValueObject

_BODY_MAX_LENGTH = 20000
_SUMMARY_MAX_LENGTH = 500
_SUMMARY_GENERATED_LENGTH = 200

_MARKDOWN_STRIP_RE = re.compile(r"[#*_`>\[\]!]")
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class AnswerId(ValueObject):
    value: UUID

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class AnswerBody(ValueObject):
    """The answer's own content — always required, unlike `AnswerSummary`
    (which may be caller-omitted and auto-derived, see that class's own
    docstring)."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise AnswerBodyRequiredError()
        if len(stripped) > _BODY_MAX_LENGTH:
            raise AnswerBodyTooLongError(_BODY_MAX_LENGTH)
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class AnswerSummary(ValueObject):
    """A short summary of the answer body — always populated on the
    entity (either caller-supplied or auto-derived via `from_body`), the
    same non-optional-on-the-entity shape `CommunityQuestion.summary`
    already establishes for itself."""

    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise AnswerSummaryRequiredError()
        if len(stripped) > _SUMMARY_MAX_LENGTH:
            raise AnswerSummaryTooLongError(_SUMMARY_MAX_LENGTH)
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_body(cls, body: str) -> "AnswerSummary":
        if not body.strip():
            raise AnswerBodyRequiredError()
        plain = _MARKDOWN_STRIP_RE.sub("", body)
        plain = _WHITESPACE_RE.sub(" ", plain).strip()
        if len(plain) <= _SUMMARY_GENERATED_LENGTH:
            return cls(plain)
        truncated = plain[:_SUMMARY_GENERATED_LENGTH].rsplit(" ", 1)[0].rstrip(".,;:!?")
        return cls(f"{truncated}...")

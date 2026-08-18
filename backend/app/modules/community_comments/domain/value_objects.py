"""Value objects specific to the Community Comments module.

`CommentId` mirrors `app.modules.community_answers.domain.value_objects
.AnswerId` exactly — a strongly-typed wrapper used only as the
cross-aggregate *reference* field (`CommunityCommentRevision.comment_id`,
`CommunityCommentAttachment.comment_id`), never as `CommunityComment.id`
itself (which stays a plain `UUID`, like every other aggregate root).

`CommentBody` mirrors `AnswerBody` — non-blank, length-bounded. There is
deliberately no `CommentSummary`-equivalent value object: this task's own
DOMAIN section names only the three entities (`CommunityComment`,
`CommunityCommentRevision`, `CommunityCommentAttachment`) and leaves
"appropriate" value objects to this module's own judgment — unlike a
long-form Post/Question/Answer body, a comment's own body is short enough
that a separate list-view summary/excerpt serves no purpose here, and
nothing in this task's API/APPLICATION sections asks for one, so
inventing one would be unrequested abstraction.
"""

from dataclasses import dataclass
from uuid import UUID

from app.modules.community_comments.domain.exceptions import (
    CommentBodyRequiredError,
    CommentBodyTooLongError,
)
from app.shared.domain.value_object import ValueObject

_BODY_MAX_LENGTH = 10000


@dataclass(frozen=True, slots=True)
class CommentId(ValueObject):
    value: UUID

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class CommentBody(ValueObject):
    value: str

    def __post_init__(self) -> None:
        stripped = self.value.strip()
        if not stripped:
            raise CommentBodyRequiredError()
        if len(stripped) > _BODY_MAX_LENGTH:
            raise CommentBodyTooLongError(_BODY_MAX_LENGTH)
        object.__setattr__(self, "value", stripped)

    def __str__(self) -> str:
        return self.value

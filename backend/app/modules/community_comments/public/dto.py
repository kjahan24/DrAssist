"""Public DTOs — the only data shapes another module may depend on.

Re-exported from the application layer's `dto.py`, not redefined, so
there is exactly one definition of each shape — the same precedent
`app.modules.community_answers.public.dto` already establishes.

`CommunityCommentSummaryDTO.author_id` stays `UUID | None` here too — see
that dataclass's own docstring in `application/dto.py`: any future
consumer module (Votes, Notifications, Moderation, AI Analysis) reading
this DTO sees the same anonymous-masked shape the public API itself
returns.
"""

from app.modules.community_comments.application.dto import CommunityCommentSummaryDTO
from app.modules.community_comments.domain.enums import CommentStatus, CommentTargetType

__all__ = ["CommentStatus", "CommentTargetType", "CommunityCommentSummaryDTO"]

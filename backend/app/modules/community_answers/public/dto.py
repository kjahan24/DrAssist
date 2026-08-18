"""Public DTOs — the only data shapes another module may depend on.

Re-exported from the application layer's `dto.py`, not redefined, so
there is exactly one definition of each shape — the same precedent
`app.modules.community_questions.public.dto` already establishes.

`CommunityAnswerSummaryDTO.author_id` stays `UUID | None` here too — see
that dataclass's own docstring in `application/dto.py`: any future
consumer module (Votes, Comments, AI Analysis) reading this DTO sees the
same anonymous-masked shape the public API itself returns.
"""

from app.modules.community_answers.application.dto import CommunityAnswerSummaryDTO
from app.modules.community_answers.domain.enums import AnswerStatus, AnswerVisibility

__all__ = ["CommunityAnswerSummaryDTO", "AnswerStatus", "AnswerVisibility"]

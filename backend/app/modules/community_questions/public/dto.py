"""Public DTOs — the only data shapes another module may depend on.

Re-exported from the application layer's `dto.py`, not redefined, so
there is exactly one definition of each shape — the same precedent
`app.modules.community_posts.public.dto` already establishes.
"""

from app.modules.community_questions.application.dto import CommunityQuestionSummaryDTO
from app.modules.community_questions.domain.enums import (
    QuestionStatus,
    QuestionType,
    QuestionVisibility,
)

__all__ = ["CommunityQuestionSummaryDTO", "QuestionStatus", "QuestionType", "QuestionVisibility"]

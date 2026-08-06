"""Public DTOs — the only data shapes another module may depend on.

Re-exported from the application layer's `dto.py`, not redefined, so
there is exactly one definition of each shape — the same "exactly one
definition" precedent every prior module's own `public/dto.py`
establishes for itself.
"""

from app.modules.community_posts.application.dto import CommunityPostSummaryDTO
from app.modules.community_posts.domain.enums import PostStatus, PostType, PostVisibility

__all__ = ["CommunityPostSummaryDTO", "PostStatus", "PostType", "PostVisibility"]

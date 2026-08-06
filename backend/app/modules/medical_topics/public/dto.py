"""Public DTOs — the only data shapes another module may depend on.

Re-exported from the application layer's `dto.py`, not redefined, so
there is exactly one definition of each shape — the same "exactly one
definition" precedent `app.modules.community.public.dto` establishes for
itself.
"""

from app.modules.medical_topics.application.dto import TopicSummaryDTO
from app.modules.medical_topics.domain.enums import TopicStatus, TopicVisibility

__all__ = ["TopicStatus", "TopicSummaryDTO", "TopicVisibility"]

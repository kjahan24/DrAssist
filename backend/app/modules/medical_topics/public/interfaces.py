"""The Medical Topics module's public port — the only contract another
module may depend on. See
`docs/backend-architecture/03_module_architecture.md` and
`10_module_communication.md`.

Never import from `app.modules.medical_topics.domain`, `.application`
(beyond this package's own re-exports in `public/dto.py`), or
`.infrastructure` from outside this module — this file and `dto.py` are
the entire allowed surface today.

This is the read-only lookup port this task's own GOAL section calls
for: Communities/Posts/Questions/Answers/AI recommendation/Search all
need to resolve a topic id into a summary (or confirm one exists) without
depending on this module's own repositories/entities — the same
"query port for future consumer modules" shape
`app.modules.community.public.interfaces.CommunityQueryPort` already
establishes for itself.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.medical_topics.public.dto import TopicSummaryDTO


class TopicQueryPort(ABC):
    @abstractmethod
    async def topic_exists(self, topic_id: UUID) -> bool: ...

    @abstractmethod
    async def get_topic_summary(self, topic_id: UUID) -> TopicSummaryDTO | None: ...

    @abstractmethod
    async def get_topic_summary_by_slug(self, slug: str) -> TopicSummaryDTO | None: ...

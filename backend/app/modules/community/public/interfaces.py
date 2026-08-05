"""The Community module's public port — the only contract another module
may depend on. See `docs/backend-architecture/03_module_architecture.md`
and `10_module_communication.md`.

Never import from `app.modules.community.domain`, `.application` (beyond
this package's own re-exports in `public/dto.py`), or `.infrastructure`
from outside this module — this file and `dto.py` are the entire allowed
surface today.

`get_membership`/`is_active_member` exist specifically for the future
Posts/Questions/Answers/Comments modules this task's own GOAL section
names as "separate modules" — each of those will need to check "is this
caller a member of the community they're posting into, and with what
role" without depending on this module's own repositories/entities.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.community.public.dto import CommunityMemberSummaryDTO, CommunitySummaryDTO


class CommunityQueryPort(ABC):
    @abstractmethod
    async def community_exists(self, community_id: UUID) -> bool: ...

    @abstractmethod
    async def get_community_summary(self, community_id: UUID) -> CommunitySummaryDTO | None: ...

    @abstractmethod
    async def get_membership(
        self, community_id: UUID, user_id: UUID
    ) -> CommunityMemberSummaryDTO | None: ...

    @abstractmethod
    async def is_active_member(self, community_id: UUID, user_id: UUID) -> bool: ...

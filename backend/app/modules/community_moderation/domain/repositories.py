"""Repository interfaces (ports) for the Community Moderation module.
Concrete implementations live in `infrastructure/repositories.py`; the
application layer depends only on these ABCs.

`ModerationActionRepository` has no `remove()` at all — this task's own
"Never delete audit history through normal APIs" is enforced structurally
by the port simply not offering a way to, the same as
`app.modules.audit_log.domain.repositories.AuditLogRepository`.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from app.modules.community_moderation.domain.entities import (
    CommunityReport,
    DoctorVerification,
    ModerationAction,
    ModerationRestriction,
)
from app.modules.community_moderation.domain.enums import (
    ModerationTargetType,
    ReportPriority,
    ReportStatus,
)


class CommunityReportRepository(ABC):
    @abstractmethod
    async def get_by_id(self, report_id: UUID) -> CommunityReport | None: ...

    @abstractmethod
    async def get_open_report(
        self, reporter_id: UUID, target_type: ModerationTargetType, target_id: UUID
    ) -> CommunityReport | None:
        """The most recent report by `reporter_id` against this target
        whose `status` is `OPEN`/`UNDER_REVIEW` — `None` if none exists,
        which is what makes filing a new report legal again after a prior
        one is resolved/rejected. Backs `DuplicateOpenReportError`."""
        ...

    @abstractmethod
    async def list_reports(
        self,
        *,
        organization_id: UUID,
        community_id: UUID | None = None,
        status: ReportStatus | None = None,
        priority: ReportPriority | None = None,
        assigned_moderator_id: UUID | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[Sequence[CommunityReport], str | None]: ...

    @abstractmethod
    async def add(self, report: CommunityReport) -> None: ...


class ModerationActionRepository(ABC):
    @abstractmethod
    async def get_by_id(self, action_id: UUID) -> ModerationAction | None: ...

    @abstractmethod
    async def get_latest_for_target(
        self, target_type: ModerationTargetType, target_id: UUID
    ) -> ModerationAction | None:
        """The most recently recorded action for this target — the sole
        source of truth for "current moderation status," per this
        entity's own module docstring."""
        ...

    @abstractmethod
    async def list_for_target(
        self,
        target_type: ModerationTargetType,
        target_id: UUID,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[Sequence[ModerationAction], str | None]: ...

    @abstractmethod
    async def list_for_actor(
        self, actor_id: UUID, *, cursor: str | None = None, limit: int = 20
    ) -> tuple[Sequence[ModerationAction], str | None]: ...

    @abstractmethod
    async def add(self, action: ModerationAction) -> None: ...


class ModerationRestrictionRepository(ABC):
    @abstractmethod
    async def get_by_id(self, restriction_id: UUID) -> ModerationRestriction | None: ...

    @abstractmethod
    async def list_active_for_user(
        self,
        user_id: UUID,
        *,
        community_id: UUID | None = None,
        now: datetime | None = None,
    ) -> Sequence[ModerationRestriction]:
        """Every restriction for `user_id` (optionally scoped to
        `community_id`) whose `is_active(now=now)` is currently `True` —
        backs `GetModerationStatusService`."""
        ...

    @abstractmethod
    async def list_for_user(
        self, user_id: UUID, *, cursor: str | None = None, limit: int = 20
    ) -> tuple[Sequence[ModerationRestriction], str | None]: ...

    @abstractmethod
    async def add(self, restriction: ModerationRestriction) -> None: ...


class DoctorVerificationRepository(ABC):
    @abstractmethod
    async def get_by_id(self, verification_id: UUID) -> DoctorVerification | None: ...

    @abstractmethod
    async def get_by_doctor_id(self, doctor_id: UUID) -> DoctorVerification | None: ...

    @abstractmethod
    async def add(self, verification: DoctorVerification) -> None: ...

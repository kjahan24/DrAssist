"""Concrete SQLAlchemy repository implementations.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — the same pattern every prior module's own
`infrastructure/repositories.py` establishes. `ModerationActionRepository`
has no `remove()` at all — see `domain/repositories.py`'s own docstring.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.

Every cursor-paginated `list_*` method here shares the identical
`(created_at, id)` keyset-pagination shape
`app.modules.community_engagement.infrastructure.repositories` already
establishes.
"""

import base64
from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.modules.community_moderation.domain.repositories import (
    CommunityReportRepository,
    DoctorVerificationRepository,
    ModerationActionRepository,
    ModerationRestrictionRepository,
)
from app.modules.community_moderation.infrastructure.mappers import (
    action_to_domain,
    apply_action_to_model,
    apply_report_to_model,
    apply_restriction_to_model,
    apply_verification_to_model,
    report_to_domain,
    restriction_to_domain,
    verification_to_domain,
)
from app.modules.community_moderation.infrastructure.models import (
    CommunityReportModel,
    DoctorVerificationModel,
    ModerationActionModel,
    ModerationRestrictionModel,
)

_CURSOR_SEPARATOR = "|"
_OPEN_STATUSES = (ReportStatus.OPEN, ReportStatus.UNDER_REVIEW)


def _encode_cursor(created_at: datetime, row_id: UUID) -> str:
    payload = f"{created_at.isoformat()}{_CURSOR_SEPARATOR}{row_id}"
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    payload = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    created_at_raw, row_id_raw = payload.split(_CURSOR_SEPARATOR, 1)
    return datetime.fromisoformat(created_at_raw), UUID(row_id_raw)


class SqlAlchemyCommunityReportRepository(CommunityReportRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, report_id: UUID) -> CommunityReport | None:
        model = await self._session.get(CommunityReportModel, report_id)
        return report_to_domain(model) if model is not None else None

    async def get_open_report(
        self, reporter_id: UUID, target_type: ModerationTargetType, target_id: UUID
    ) -> CommunityReport | None:
        stmt = (
            select(CommunityReportModel)
            .where(
                CommunityReportModel.reporter_id == reporter_id,
                CommunityReportModel.target_type == target_type,
                CommunityReportModel.target_id == target_id,
                CommunityReportModel.status.in_(_OPEN_STATUSES),
            )
            .order_by(CommunityReportModel.created_at.desc())
            .limit(1)
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return report_to_domain(model) if model is not None else None

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
    ) -> tuple[Sequence[CommunityReport], str | None]:
        conditions = [CommunityReportModel.organization_id == organization_id]
        if community_id is not None:
            conditions.append(CommunityReportModel.community_id == community_id)
        if status is not None:
            conditions.append(CommunityReportModel.status == status)
        if priority is not None:
            conditions.append(CommunityReportModel.priority == priority)
        if assigned_moderator_id is not None:
            conditions.append(CommunityReportModel.assigned_moderator_id == assigned_moderator_id)
        if cursor is not None:
            cursor_created_at, cursor_id = _decode_cursor(cursor)
            conditions.append(
                or_(
                    CommunityReportModel.created_at < cursor_created_at,
                    and_(
                        CommunityReportModel.created_at == cursor_created_at,
                        CommunityReportModel.id < cursor_id,
                    ),
                )
            )

        stmt = (
            select(CommunityReportModel)
            .where(*conditions)
            .order_by(CommunityReportModel.created_at.desc(), CommunityReportModel.id.desc())
            .limit(limit + 1)
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        has_more = len(rows) > limit
        page = rows[:limit]
        next_cursor = (
            _encode_cursor(page[-1].created_at, page[-1].id) if has_more and page else None
        )
        return [report_to_domain(m) for m in page], next_cursor

    async def add(self, report: CommunityReport) -> None:
        model = await self._session.get(CommunityReportModel, report.id)
        if model is None:
            model = CommunityReportModel()
            self._session.add(model)
        apply_report_to_model(report, model)


class SqlAlchemyModerationActionRepository(ModerationActionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, action_id: UUID) -> ModerationAction | None:
        model = await self._session.get(ModerationActionModel, action_id)
        return action_to_domain(model) if model is not None else None

    async def get_latest_for_target(
        self, target_type: ModerationTargetType, target_id: UUID
    ) -> ModerationAction | None:
        stmt = (
            select(ModerationActionModel)
            .where(
                ModerationActionModel.target_type == target_type,
                ModerationActionModel.target_id == target_id,
            )
            .order_by(ModerationActionModel.created_at.desc())
            .limit(1)
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return action_to_domain(model) if model is not None else None

    async def list_for_target(
        self,
        target_type: ModerationTargetType,
        target_id: UUID,
        *,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[Sequence[ModerationAction], str | None]:
        conditions = [
            ModerationActionModel.target_type == target_type,
            ModerationActionModel.target_id == target_id,
        ]
        if cursor is not None:
            cursor_created_at, cursor_id = _decode_cursor(cursor)
            conditions.append(
                or_(
                    ModerationActionModel.created_at < cursor_created_at,
                    and_(
                        ModerationActionModel.created_at == cursor_created_at,
                        ModerationActionModel.id < cursor_id,
                    ),
                )
            )
        stmt = (
            select(ModerationActionModel)
            .where(*conditions)
            .order_by(ModerationActionModel.created_at.desc(), ModerationActionModel.id.desc())
            .limit(limit + 1)
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        has_more = len(rows) > limit
        page = rows[:limit]
        next_cursor = (
            _encode_cursor(page[-1].created_at, page[-1].id) if has_more and page else None
        )
        return [action_to_domain(m) for m in page], next_cursor

    async def list_for_actor(
        self, actor_id: UUID, *, cursor: str | None = None, limit: int = 20
    ) -> tuple[Sequence[ModerationAction], str | None]:
        conditions = [ModerationActionModel.actor_id == actor_id]
        if cursor is not None:
            cursor_created_at, cursor_id = _decode_cursor(cursor)
            conditions.append(
                or_(
                    ModerationActionModel.created_at < cursor_created_at,
                    and_(
                        ModerationActionModel.created_at == cursor_created_at,
                        ModerationActionModel.id < cursor_id,
                    ),
                )
            )
        stmt = (
            select(ModerationActionModel)
            .where(*conditions)
            .order_by(ModerationActionModel.created_at.desc(), ModerationActionModel.id.desc())
            .limit(limit + 1)
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        has_more = len(rows) > limit
        page = rows[:limit]
        next_cursor = (
            _encode_cursor(page[-1].created_at, page[-1].id) if has_more and page else None
        )
        return [action_to_domain(m) for m in page], next_cursor

    async def add(self, action: ModerationAction) -> None:
        model = await self._session.get(ModerationActionModel, action.id)
        if model is None:
            model = ModerationActionModel()
            self._session.add(model)
        apply_action_to_model(action, model)


class SqlAlchemyModerationRestrictionRepository(ModerationRestrictionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, restriction_id: UUID) -> ModerationRestriction | None:
        model = await self._session.get(ModerationRestrictionModel, restriction_id)
        return restriction_to_domain(model) if model is not None else None

    async def list_active_for_user(
        self,
        user_id: UUID,
        *,
        community_id: UUID | None = None,
        now: datetime | None = None,
    ) -> Sequence[ModerationRestriction]:
        current = now if now is not None else datetime.now(UTC)
        conditions = [
            ModerationRestrictionModel.user_id == user_id,
            ModerationRestrictionModel.starts_at <= current,
            or_(
                ModerationRestrictionModel.ends_at.is_(None),
                ModerationRestrictionModel.ends_at > current,
            ),
        ]
        if community_id is not None:
            conditions.append(ModerationRestrictionModel.community_id == community_id)
        stmt = select(ModerationRestrictionModel).where(*conditions)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [restriction_to_domain(m) for m in rows]

    async def list_for_user(
        self, user_id: UUID, *, cursor: str | None = None, limit: int = 20
    ) -> tuple[Sequence[ModerationRestriction], str | None]:
        conditions = [ModerationRestrictionModel.user_id == user_id]
        if cursor is not None:
            cursor_created_at, cursor_id = _decode_cursor(cursor)
            conditions.append(
                or_(
                    ModerationRestrictionModel.created_at < cursor_created_at,
                    and_(
                        ModerationRestrictionModel.created_at == cursor_created_at,
                        ModerationRestrictionModel.id < cursor_id,
                    ),
                )
            )
        stmt = (
            select(ModerationRestrictionModel)
            .where(*conditions)
            .order_by(
                ModerationRestrictionModel.created_at.desc(), ModerationRestrictionModel.id.desc()
            )
            .limit(limit + 1)
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        has_more = len(rows) > limit
        page = rows[:limit]
        next_cursor = (
            _encode_cursor(page[-1].created_at, page[-1].id) if has_more and page else None
        )
        return [restriction_to_domain(m) for m in page], next_cursor

    async def add(self, restriction: ModerationRestriction) -> None:
        model = await self._session.get(ModerationRestrictionModel, restriction.id)
        if model is None:
            model = ModerationRestrictionModel()
            self._session.add(model)
        apply_restriction_to_model(restriction, model)


class SqlAlchemyDoctorVerificationRepository(DoctorVerificationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, verification_id: UUID) -> DoctorVerification | None:
        model = await self._session.get(DoctorVerificationModel, verification_id)
        return verification_to_domain(model) if model is not None else None

    async def get_by_doctor_id(self, doctor_id: UUID) -> DoctorVerification | None:
        stmt = select(DoctorVerificationModel).where(DoctorVerificationModel.doctor_id == doctor_id)
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return verification_to_domain(model) if model is not None else None

    async def add(self, verification: DoctorVerification) -> None:
        model = await self._session.get(DoctorVerificationModel, verification.id)
        if model is None:
            model = DoctorVerificationModel()
            self._session.add(model)
        apply_verification_to_model(verification, model)

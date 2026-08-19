"""Concrete SQLAlchemy repository for the Community AI Features module.

`add()` is upsert — look up by id, create if missing, overwrite mapped
columns from the entity's current in-memory state — the identical
pattern every prior module's own `infrastructure/repositories.py`
establishes (see `community_moderation`'s own docstring). No
`session.commit()` here — exclusively the `UnitOfWork`'s responsibility.

`list_analyses` shares the identical `(created_at, id)` keyset-pagination
shape `community_moderation`/`community_engagement`'s own repositories
already establish.
"""

import base64
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.community_ai.domain.entities import AICommunityAnalysis
from app.modules.community_ai.domain.enums import (
    AIAnalysisStatus,
    AIAnalysisType,
    CommunityContentTargetType,
)
from app.modules.community_ai.domain.repositories import AICommunityAnalysisRepository
from app.modules.community_ai.infrastructure.mappers import (
    analysis_to_domain,
    apply_analysis_to_model,
)
from app.modules.community_ai.infrastructure.models import CommunityAIAnalysisModel

_CURSOR_SEPARATOR = "|"


def _encode_cursor(created_at: datetime, row_id: UUID) -> str:
    payload = f"{created_at.isoformat()}{_CURSOR_SEPARATOR}{row_id}"
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    payload = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    created_at_raw, row_id_raw = payload.split(_CURSOR_SEPARATOR, 1)
    return datetime.fromisoformat(created_at_raw), UUID(row_id_raw)


class SqlAlchemyAICommunityAnalysisRepository(AICommunityAnalysisRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, analysis_id: UUID) -> AICommunityAnalysis | None:
        model = await self._session.get(CommunityAIAnalysisModel, analysis_id)
        return analysis_to_domain(model) if model is not None else None

    async def get_by_target(
        self,
        target_type: CommunityContentTargetType,
        target_id: UUID,
        analysis_type: AIAnalysisType,
    ) -> AICommunityAnalysis | None:
        stmt = select(CommunityAIAnalysisModel).where(
            CommunityAIAnalysisModel.target_type == target_type,
            CommunityAIAnalysisModel.target_id == target_id,
            CommunityAIAnalysisModel.analysis_type == analysis_type,
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return analysis_to_domain(model) if model is not None else None

    async def list_analyses(
        self,
        *,
        organization_id: UUID,
        target_type: CommunityContentTargetType | None = None,
        target_id: UUID | None = None,
        analysis_type: AIAnalysisType | None = None,
        status: AIAnalysisStatus | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> tuple[Sequence[AICommunityAnalysis], str | None]:
        conditions = [CommunityAIAnalysisModel.organization_id == organization_id]
        if target_type is not None:
            conditions.append(CommunityAIAnalysisModel.target_type == target_type)
        if target_id is not None:
            conditions.append(CommunityAIAnalysisModel.target_id == target_id)
        if analysis_type is not None:
            conditions.append(CommunityAIAnalysisModel.analysis_type == analysis_type)
        if status is not None:
            conditions.append(CommunityAIAnalysisModel.status == status)
        if cursor is not None:
            cursor_created_at, cursor_id = _decode_cursor(cursor)
            conditions.append(
                or_(
                    CommunityAIAnalysisModel.created_at < cursor_created_at,
                    and_(
                        CommunityAIAnalysisModel.created_at == cursor_created_at,
                        CommunityAIAnalysisModel.id < cursor_id,
                    ),
                )
            )

        stmt = (
            select(CommunityAIAnalysisModel)
            .where(*conditions)
            .order_by(
                CommunityAIAnalysisModel.created_at.desc(), CommunityAIAnalysisModel.id.desc()
            )
            .limit(limit + 1)
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        has_more = len(rows) > limit
        page = rows[:limit]
        next_cursor = (
            _encode_cursor(page[-1].created_at, page[-1].id) if has_more and page else None
        )
        return [analysis_to_domain(m) for m in page], next_cursor

    async def add(self, analysis: AICommunityAnalysis) -> None:
        model = await self._session.get(CommunityAIAnalysisModel, analysis.id)
        if model is None:
            model = CommunityAIAnalysisModel()
            self._session.add(model)
        apply_analysis_to_model(analysis, model)

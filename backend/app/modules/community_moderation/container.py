"""Composition root for the Community Moderation module's public surface.
`build_moderation_facade` is the only factory a peer module should call —
never construct `ModerationFacade` or its repositories directly."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.community_moderation.infrastructure.repositories import (
    SqlAlchemyDoctorVerificationRepository,
    SqlAlchemyModerationActionRepository,
    SqlAlchemyModerationRestrictionRepository,
)
from app.modules.community_moderation.public.facade import ModerationFacade


def build_moderation_facade(session: AsyncSession) -> ModerationFacade:
    """Construct a `ModerationFacade` wired to `session`."""
    return ModerationFacade(
        action_repository=SqlAlchemyModerationActionRepository(session),
        restriction_repository=SqlAlchemyModerationRestrictionRepository(session),
        verification_repository=SqlAlchemyDoctorVerificationRepository(session),
    )

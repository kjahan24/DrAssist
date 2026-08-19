"""Unit tests confirming `public/dto.py` re-exports the correct shapes
without redefining them."""

from app.modules.community_moderation.application.dto import (
    VerificationSummaryDTO as ApplicationVerificationSummaryDTO,
)
from app.modules.community_moderation.domain.enums import (
    ModerationTargetType as DomainModerationTargetType,
)
from app.modules.community_moderation.domain.enums import (
    VerificationStatus as DomainVerificationStatus,
)
from app.modules.community_moderation.domain.value_objects import (
    UserModerationStatus as DomainUserModerationStatus,
)
from app.modules.community_moderation.public.dto import (
    ModerationTargetType,
    UserModerationStatus,
    VerificationStatus,
    VerificationSummaryDTO,
)


class TestPublicDtoReExports:
    def test_verification_summary_dto_is_the_application_type(self) -> None:
        assert VerificationSummaryDTO is ApplicationVerificationSummaryDTO

    def test_moderation_target_type_is_the_domain_type(self) -> None:
        assert ModerationTargetType is DomainModerationTargetType

    def test_verification_status_is_the_domain_type(self) -> None:
        assert VerificationStatus is DomainVerificationStatus

    def test_user_moderation_status_is_the_domain_type(self) -> None:
        assert UserModerationStatus is DomainUserModerationStatus

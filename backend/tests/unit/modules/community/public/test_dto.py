"""Unit tests confirming `public/dto.py` re-exports the correct shapes
without redefining them."""

from app.modules.community.application.dto import (
    CommunityMemberSummaryDTO as ApplicationCommunityMemberSummaryDTO,
)
from app.modules.community.application.dto import (
    CommunitySummaryDTO as ApplicationCommunitySummaryDTO,
)
from app.modules.community.domain.enums import (
    CommunityMemberStatus as DomainCommunityMemberStatus,
)
from app.modules.community.domain.enums import CommunityRole as DomainCommunityRole
from app.modules.community.domain.enums import CommunityVisibility as DomainCommunityVisibility
from app.modules.community.public.dto import (
    CommunityMemberStatus,
    CommunityMemberSummaryDTO,
    CommunityRole,
    CommunitySummaryDTO,
    CommunityVisibility,
)


class TestPublicDtoReExports:
    def test_community_summary_dto_is_the_application_type(self) -> None:
        assert CommunitySummaryDTO is ApplicationCommunitySummaryDTO

    def test_community_member_summary_dto_is_the_application_type(self) -> None:
        assert CommunityMemberSummaryDTO is ApplicationCommunityMemberSummaryDTO

    def test_community_visibility_is_the_domain_type(self) -> None:
        assert CommunityVisibility is DomainCommunityVisibility

    def test_community_role_is_the_domain_type(self) -> None:
        assert CommunityRole is DomainCommunityRole

    def test_community_member_status_is_the_domain_type(self) -> None:
        assert CommunityMemberStatus is DomainCommunityMemberStatus

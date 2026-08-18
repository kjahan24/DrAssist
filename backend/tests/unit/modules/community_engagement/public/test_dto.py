"""Unit tests confirming `public/dto.py` re-exports the correct shapes
without redefining them."""

from app.modules.community_engagement.application.dto import (
    VoteCountsDTO as ApplicationVoteCountsDTO,
)
from app.modules.community_engagement.domain.enums import (
    EngagementTargetType as DomainEngagementTargetType,
)
from app.modules.community_engagement.domain.enums import VoteType as DomainVoteType
from app.modules.community_engagement.public.dto import (
    EngagementTargetType,
    VoteCountsDTO,
    VoteType,
)


class TestPublicDtoReExports:
    def test_vote_counts_dto_is_the_application_type(self) -> None:
        assert VoteCountsDTO is ApplicationVoteCountsDTO

    def test_engagement_target_type_is_the_domain_type(self) -> None:
        assert EngagementTargetType is DomainEngagementTargetType

    def test_vote_type_is_the_domain_type(self) -> None:
        assert VoteType is DomainVoteType

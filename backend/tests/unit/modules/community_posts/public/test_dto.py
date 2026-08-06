"""Unit tests confirming `public/dto.py` re-exports the correct shapes
without redefining them."""

from app.modules.community_posts.application.dto import (
    CommunityPostSummaryDTO as ApplicationCommunityPostSummaryDTO,
)
from app.modules.community_posts.domain.enums import PostStatus as DomainPostStatus
from app.modules.community_posts.domain.enums import PostType as DomainPostType
from app.modules.community_posts.domain.enums import PostVisibility as DomainPostVisibility
from app.modules.community_posts.public.dto import (
    CommunityPostSummaryDTO,
    PostStatus,
    PostType,
    PostVisibility,
)


class TestPublicDtoReExports:
    def test_community_post_summary_dto_is_the_application_type(self) -> None:
        assert CommunityPostSummaryDTO is ApplicationCommunityPostSummaryDTO

    def test_post_status_is_the_domain_type(self) -> None:
        assert PostStatus is DomainPostStatus

    def test_post_type_is_the_domain_type(self) -> None:
        assert PostType is DomainPostType

    def test_post_visibility_is_the_domain_type(self) -> None:
        assert PostVisibility is DomainPostVisibility

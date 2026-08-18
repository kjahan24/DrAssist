"""Unit tests confirming `public/dto.py` re-exports the correct shapes
without redefining them."""

from app.modules.community_comments.application.dto import (
    CommunityCommentSummaryDTO as ApplicationCommunityCommentSummaryDTO,
)
from app.modules.community_comments.domain.enums import CommentStatus as DomainCommentStatus
from app.modules.community_comments.domain.enums import (
    CommentTargetType as DomainCommentTargetType,
)
from app.modules.community_comments.public.dto import (
    CommentStatus,
    CommentTargetType,
    CommunityCommentSummaryDTO,
)


class TestPublicDtoReExports:
    def test_community_comment_summary_dto_is_the_application_type(self) -> None:
        assert CommunityCommentSummaryDTO is ApplicationCommunityCommentSummaryDTO

    def test_comment_status_is_the_domain_type(self) -> None:
        assert CommentStatus is DomainCommentStatus

    def test_comment_target_type_is_the_domain_type(self) -> None:
        assert CommentTargetType is DomainCommentTargetType

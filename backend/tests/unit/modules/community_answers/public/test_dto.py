"""Unit tests confirming `public/dto.py` re-exports the correct shapes
without redefining them."""

from app.modules.community_answers.application.dto import (
    CommunityAnswerSummaryDTO as ApplicationCommunityAnswerSummaryDTO,
)
from app.modules.community_answers.domain.enums import AnswerStatus as DomainAnswerStatus
from app.modules.community_answers.domain.enums import AnswerVisibility as DomainAnswerVisibility
from app.modules.community_answers.public.dto import (
    AnswerStatus,
    AnswerVisibility,
    CommunityAnswerSummaryDTO,
)


class TestPublicDtoReExports:
    def test_community_answer_summary_dto_is_the_application_type(self) -> None:
        assert CommunityAnswerSummaryDTO is ApplicationCommunityAnswerSummaryDTO

    def test_answer_status_is_the_domain_type(self) -> None:
        assert AnswerStatus is DomainAnswerStatus

    def test_answer_visibility_is_the_domain_type(self) -> None:
        assert AnswerVisibility is DomainAnswerVisibility

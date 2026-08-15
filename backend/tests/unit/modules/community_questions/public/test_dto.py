"""Unit tests confirming `public/dto.py` re-exports the correct shapes
without redefining them."""

from app.modules.community_questions.application.dto import (
    CommunityQuestionSummaryDTO as ApplicationCommunityQuestionSummaryDTO,
)
from app.modules.community_questions.domain.enums import QuestionStatus as DomainQuestionStatus
from app.modules.community_questions.domain.enums import QuestionType as DomainQuestionType
from app.modules.community_questions.domain.enums import (
    QuestionVisibility as DomainQuestionVisibility,
)
from app.modules.community_questions.public.dto import (
    CommunityQuestionSummaryDTO,
    QuestionStatus,
    QuestionType,
    QuestionVisibility,
)


class TestPublicDtoReExports:
    def test_community_question_summary_dto_is_the_application_type(self) -> None:
        assert CommunityQuestionSummaryDTO is ApplicationCommunityQuestionSummaryDTO

    def test_question_status_is_the_domain_type(self) -> None:
        assert QuestionStatus is DomainQuestionStatus

    def test_question_type_is_the_domain_type(self) -> None:
        assert QuestionType is DomainQuestionType

    def test_question_visibility_is_the_domain_type(self) -> None:
        assert QuestionVisibility is DomainQuestionVisibility

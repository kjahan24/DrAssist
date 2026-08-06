"""Unit tests confirming `public/dto.py` re-exports the correct shapes
without redefining them."""

from app.modules.medical_topics.application.dto import TopicSummaryDTO as ApplicationTopicSummaryDTO
from app.modules.medical_topics.domain.enums import TopicStatus as DomainTopicStatus
from app.modules.medical_topics.domain.enums import TopicVisibility as DomainTopicVisibility
from app.modules.medical_topics.public.dto import TopicStatus, TopicSummaryDTO, TopicVisibility


class TestPublicDtoReExports:
    def test_topic_summary_dto_is_the_application_type(self) -> None:
        assert TopicSummaryDTO is ApplicationTopicSummaryDTO

    def test_topic_status_is_the_domain_type(self) -> None:
        assert TopicStatus is DomainTopicStatus

    def test_topic_visibility_is_the_domain_type(self) -> None:
        assert TopicVisibility is DomainTopicVisibility

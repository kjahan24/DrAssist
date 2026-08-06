"""Unit tests for `TopicFacade` — exercised through `TopicQueryPort`
exactly as a future consumer module (Communities/Posts/Questions/...)
would call it, per
`docs/backend-architecture/12_testing_architecture.md`'s "Contract
tests" framing."""

from uuid import uuid4

from app.modules.medical_topics.application.services.topic_query_service import GetTopicService
from app.modules.medical_topics.domain.entities import MedicalTopic
from app.modules.medical_topics.domain.value_objects import TopicName, TopicSlug
from app.modules.medical_topics.public.facade import TopicFacade
from app.modules.medical_topics.public.interfaces import TopicQueryPort
from tests.unit.modules.medical_topics.application.fakes import FakeMedicalTopicRepository


def _facade() -> tuple[TopicFacade, FakeMedicalTopicRepository]:
    topics = FakeMedicalTopicRepository()
    facade = TopicFacade(query_service=GetTopicService(topic_repository=topics))
    return facade, topics


class TestTopicFacade:
    def test_is_a_topic_query_port(self) -> None:
        facade, _ = _facade()
        assert isinstance(facade, TopicQueryPort)

    async def test_topic_exists_true_when_present(self) -> None:
        facade, topics = _facade()
        topic = MedicalTopic.create(slug=TopicSlug("oncology"), name=TopicName("Oncology"))
        await topics.add(topic)

        assert await facade.topic_exists(topic.id) is True

    async def test_topic_exists_false_when_absent(self) -> None:
        facade, _ = _facade()
        assert await facade.topic_exists(uuid4()) is False

    async def test_get_topic_summary_delegates_to_the_query_service(self) -> None:
        facade, topics = _facade()
        topic = MedicalTopic.create(slug=TopicSlug("oncology"), name=TopicName("Oncology"))
        await topics.add(topic)

        summary = await facade.get_topic_summary(topic.id)

        assert summary is not None
        assert summary.topic_id == topic.id

    async def test_get_topic_summary_returns_none_for_unknown_id(self) -> None:
        facade, _ = _facade()
        assert await facade.get_topic_summary(uuid4()) is None

    async def test_get_topic_summary_by_slug_delegates_to_the_query_service(self) -> None:
        facade, topics = _facade()
        topic = MedicalTopic.create(slug=TopicSlug("oncology"), name=TopicName("Oncology"))
        await topics.add(topic)

        summary = await facade.get_topic_summary_by_slug("oncology")

        assert summary is not None
        assert summary.topic_id == topic.id

    async def test_get_topic_summary_by_slug_returns_none_for_unknown_slug(self) -> None:
        facade, _ = _facade()
        assert await facade.get_topic_summary_by_slug("unknown") is None

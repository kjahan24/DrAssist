"""Unit tests for `GetTopicService`, `ListTopicsService`,
`TopicFollowerQueryService`, and `TopicSpecialtyQueryService`, using
in-memory fakes."""

from uuid import uuid4

from app.modules.medical_topics.application.dto import ListTopicsInput
from app.modules.medical_topics.application.services.topic_query_service import (
    GetTopicService,
    ListTopicsService,
    TopicFollowerQueryService,
    TopicSpecialtyQueryService,
)
from app.modules.medical_topics.domain.entities import (
    MedicalTopic,
    MedicalTopicFollower,
    TopicSpecialty,
)
from app.modules.medical_topics.domain.value_objects import TopicId, TopicName, TopicSlug
from tests.unit.modules.medical_topics.application.fakes import (
    FakeMedicalTopicFollowerRepository,
    FakeMedicalTopicRepository,
    FakeTopicSpecialtyRepository,
)


class TestGetTopicService:
    async def test_get_by_id_returns_a_summary(self) -> None:
        topics = FakeMedicalTopicRepository()
        service = GetTopicService(topic_repository=topics)
        topic = MedicalTopic.create(slug=TopicSlug("oncology"), name=TopicName("Oncology"))
        await topics.add(topic)

        summary = await service.get_by_id(topic.id)

        assert summary is not None
        assert summary.topic_id == topic.id
        assert summary.slug == "oncology"
        assert summary.id == topic.id  # alias property

    async def test_get_by_id_returns_none_for_unknown_id(self) -> None:
        service = GetTopicService(topic_repository=FakeMedicalTopicRepository())
        assert await service.get_by_id(uuid4()) is None

    async def test_get_by_slug_returns_a_summary(self) -> None:
        topics = FakeMedicalTopicRepository()
        service = GetTopicService(topic_repository=topics)
        topic = MedicalTopic.create(slug=TopicSlug("oncology"), name=TopicName("Oncology"))
        await topics.add(topic)

        summary = await service.get_by_slug("oncology")

        assert summary is not None
        assert summary.topic_id == topic.id

    async def test_get_by_slug_returns_none_for_unknown_slug(self) -> None:
        service = GetTopicService(topic_repository=FakeMedicalTopicRepository())
        assert await service.get_by_slug("unknown") is None


class TestListTopicsService:
    async def test_lists_all_topics(self) -> None:
        topics = FakeMedicalTopicRepository()
        service = ListTopicsService(topic_repository=topics)
        topic = MedicalTopic.create(slug=TopicSlug("oncology"), name=TopicName("Oncology"))
        await topics.add(topic)

        result = await service.list_topics(ListTopicsInput())

        assert result.total == 1
        assert result.items[0].topic_id == topic.id

    async def test_filters_by_specialty_id(self) -> None:
        topics = FakeMedicalTopicRepository()
        service = ListTopicsService(topic_repository=topics)
        specialty_id = uuid4()
        matching = MedicalTopic.create(
            slug=TopicSlug("oncology"), name=TopicName("Oncology"), specialty_id=specialty_id
        )
        other = MedicalTopic.create(slug=TopicSlug("dermatology"), name=TopicName("Dermatology"))
        await topics.add(matching)
        await topics.add(other)

        result = await service.list_topics(ListTopicsInput(specialty_id=specialty_id))

        assert result.total == 1
        assert result.items[0].topic_id == matching.id

    async def test_query_filters_by_name(self) -> None:
        topics = FakeMedicalTopicRepository()
        service = ListTopicsService(topic_repository=topics)
        await topics.add(
            MedicalTopic.create(slug=TopicSlug("oncology"), name=TopicName("Oncology"))
        )
        await topics.add(
            MedicalTopic.create(slug=TopicSlug("cardiology"), name=TopicName("Cardiology"))
        )

        result = await service.list_topics(ListTopicsInput(query="onco"))

        assert result.total == 1
        assert result.items[0].slug == "oncology"

    async def test_respects_pagination(self) -> None:
        topics = FakeMedicalTopicRepository()
        service = ListTopicsService(topic_repository=topics)
        for i in range(5):
            await topics.add(
                MedicalTopic.create(slug=TopicSlug(f"topic-{i}"), name=TopicName(f"Topic {i}"))
            )

        result = await service.list_topics(ListTopicsInput(offset=2, limit=2))

        assert result.total == 5
        assert len(result.items) == 2

    async def test_list_children_returns_only_direct_children(self) -> None:
        topics = FakeMedicalTopicRepository()
        service = ListTopicsService(topic_repository=topics)
        parent = MedicalTopic.create(slug=TopicSlug("cardiology"), name=TopicName("Cardiology"))
        await topics.add(parent)
        child = MedicalTopic.create(
            slug=TopicSlug("arrhythmia"), name=TopicName("Arrhythmia"), parent_id=parent.id
        )
        await topics.add(child)
        unrelated = MedicalTopic.create(slug=TopicSlug("oncology"), name=TopicName("Oncology"))
        await topics.add(unrelated)

        children = await service.list_children(parent.id)

        assert [c.topic_id for c in children] == [child.id]

    async def test_empty_repository_returns_empty_result(self) -> None:
        service = ListTopicsService(topic_repository=FakeMedicalTopicRepository())
        result = await service.list_topics(ListTopicsInput())
        assert result.total == 0
        assert result.items == ()


class TestTopicFollowerQueryService:
    async def test_list_followers_returns_followers_of_the_topic(self) -> None:
        followers = FakeMedicalTopicFollowerRepository()
        service = TopicFollowerQueryService(follower_repository=followers)
        topic_id = uuid4()
        follower = MedicalTopicFollower.create(topic_id=TopicId(topic_id), user_id=uuid4())
        await followers.add(follower)

        results = await service.list_followers(topic_id)

        assert [f.follower_id for f in results] == [follower.id]

    async def test_count_followers(self) -> None:
        followers = FakeMedicalTopicFollowerRepository()
        service = TopicFollowerQueryService(follower_repository=followers)
        topic_id = uuid4()
        for _ in range(3):
            await followers.add(
                MedicalTopicFollower.create(topic_id=TopicId(topic_id), user_id=uuid4())
            )

        assert await service.count_followers(topic_id) == 3

    async def test_count_followers_zero_for_unfollowed_topic(self) -> None:
        service = TopicFollowerQueryService(
            follower_repository=FakeMedicalTopicFollowerRepository()
        )
        assert await service.count_followers(uuid4()) == 0

    async def test_is_following_true_when_followed(self) -> None:
        followers = FakeMedicalTopicFollowerRepository()
        service = TopicFollowerQueryService(follower_repository=followers)
        topic_id, user_id = uuid4(), uuid4()
        await followers.add(
            MedicalTopicFollower.create(topic_id=TopicId(topic_id), user_id=user_id)
        )

        assert await service.is_following(topic_id, user_id) is True

    async def test_is_following_false_when_not_followed(self) -> None:
        service = TopicFollowerQueryService(
            follower_repository=FakeMedicalTopicFollowerRepository()
        )
        assert await service.is_following(uuid4(), uuid4()) is False


class TestTopicSpecialtyQueryService:
    async def test_list_active_returns_only_active_specialties(self) -> None:
        specialties = FakeTopicSpecialtyRepository()
        service = TopicSpecialtyQueryService(specialty_repository=specialties)
        active = TopicSpecialty.create(name=TopicName("Oncology"), slug=TopicSlug("oncology"))
        inactive = TopicSpecialty.create(name=TopicName("Deprecated"), slug=TopicSlug("deprecated"))
        inactive.deactivate()
        await specialties.add(active)
        await specialties.add(inactive)

        results = await service.list_active()

        result_ids = {s.specialty_id for s in results}
        assert result_ids == {active.id}

    async def test_no_specialties_returns_empty(self) -> None:
        service = TopicSpecialtyQueryService(specialty_repository=FakeTopicSpecialtyRepository())
        assert await service.list_active() == []

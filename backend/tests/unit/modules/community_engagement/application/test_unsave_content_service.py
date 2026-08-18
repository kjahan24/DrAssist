"""Unit tests for `UnsaveContentService` — unconditionally idempotent."""

from uuid import uuid4

from app.modules.community_engagement.application.dto import UnsaveContentInput
from app.modules.community_engagement.application.services.unsave_content_service import (
    UnsaveContentService,
)
from app.modules.community_engagement.domain.entities import SavedContent
from app.modules.community_engagement.domain.enums import EngagementTargetType
from app.modules.community_engagement.domain.events import ContentUnsaved
from tests.unit.modules.community_engagement.application.fakes import (
    FakeSavedContentRepository,
    FakeUnitOfWork,
)


def _seeded() -> tuple[UnsaveContentService, FakeSavedContentRepository, FakeUnitOfWork]:
    saved = FakeSavedContentRepository()
    uow = FakeUnitOfWork()
    service = UnsaveContentService(saved_content_repository=saved, unit_of_work=uow)
    return service, saved, uow


class TestUnsaveContent:
    async def test_removes_an_existing_save(self) -> None:
        service, saved, _ = _seeded()
        user_id, target_id = uuid4(), uuid4()
        record = SavedContent.create(
            user_id=user_id,
            organization_id=uuid4(),
            target_type=EngagementTargetType.POST,
            target_id=target_id,
        )
        await saved.add(record)

        await service.execute(
            UnsaveContentInput(
                target_type=EngagementTargetType.POST, target_id=target_id, user_id=user_id
            )
        )
        assert await saved.get_saved(user_id, EngagementTargetType.POST, target_id) is None

    async def test_unsaving_something_never_saved_is_a_silent_no_op(self) -> None:
        service, _, uow = _seeded()
        await service.execute(
            UnsaveContentInput(
                target_type=EngagementTargetType.POST, target_id=uuid4(), user_id=uuid4()
            )
        )
        assert uow.committed is False

    async def test_commits_the_unit_of_work_when_a_save_is_removed(self) -> None:
        service, saved, uow = _seeded()
        user_id, target_id = uuid4(), uuid4()
        record = SavedContent.create(
            user_id=user_id,
            organization_id=uuid4(),
            target_type=EngagementTargetType.QUESTION,
            target_id=target_id,
        )
        await saved.add(record)

        await service.execute(
            UnsaveContentInput(
                target_type=EngagementTargetType.QUESTION, target_id=target_id, user_id=user_id
            )
        )
        assert uow.committed is True

    async def test_publishes_a_content_unsaved_event(self) -> None:
        service, saved, uow = _seeded()
        user_id, target_id = uuid4(), uuid4()
        record = SavedContent.create(
            user_id=user_id,
            organization_id=uuid4(),
            target_type=EngagementTargetType.ANSWER,
            target_id=target_id,
        )
        await saved.add(record)

        await service.execute(
            UnsaveContentInput(
                target_type=EngagementTargetType.ANSWER, target_id=target_id, user_id=user_id
            )
        )
        assert any(isinstance(e, ContentUnsaved) for e in uow.published_events)

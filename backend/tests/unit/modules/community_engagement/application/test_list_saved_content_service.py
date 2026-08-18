"""Unit tests for `ListSavedContentService` — cursor-paginated, scoped
always to `user_id`, never to `target_id` alone (a user's own saved list
is private to them)."""

from uuid import uuid4

from app.modules.community_engagement.application.dto import ListSavedContentInput
from app.modules.community_engagement.application.services.list_saved_content_service import (
    ListSavedContentService,
)
from app.modules.community_engagement.domain.entities import SavedContent
from app.modules.community_engagement.domain.enums import EngagementTargetType
from tests.unit.modules.community_engagement.application.fakes import FakeSavedContentRepository


def _saved(**overrides: object) -> SavedContent:
    defaults: dict[str, object] = {
        "user_id": uuid4(),
        "organization_id": uuid4(),
        "target_type": EngagementTargetType.POST,
        "target_id": uuid4(),
    }
    defaults.update(overrides)
    return SavedContent.create(**defaults)  # type: ignore[arg-type]


class TestListSavedContent:
    async def test_returns_only_the_users_own_saved_items(self) -> None:
        repo = FakeSavedContentRepository()
        service = ListSavedContentService(saved_content_repository=repo)
        org_id, user_id = uuid4(), uuid4()
        mine = _saved(user_id=user_id, organization_id=org_id)
        someone_elses = _saved(organization_id=org_id)
        await repo.add(mine)
        await repo.add(someone_elses)

        result = await service.list_saved(
            ListSavedContentInput(organization_id=org_id, user_id=user_id)
        )
        assert [i.saved_content_id for i in result.items] == [mine.id]

    async def test_filters_by_target_type(self) -> None:
        repo = FakeSavedContentRepository()
        service = ListSavedContentService(saved_content_repository=repo)
        org_id, user_id = uuid4(), uuid4()
        answer_save = _saved(
            user_id=user_id, organization_id=org_id, target_type=EngagementTargetType.ANSWER
        )
        post_save = _saved(
            user_id=user_id, organization_id=org_id, target_type=EngagementTargetType.POST
        )
        await repo.add(answer_save)
        await repo.add(post_save)

        result = await service.list_saved(
            ListSavedContentInput(
                organization_id=org_id, user_id=user_id, target_type=EngagementTargetType.ANSWER
            )
        )
        assert [i.saved_content_id for i in result.items] == [answer_save.id]

    async def test_returns_a_next_cursor_when_more_results_remain(self) -> None:
        repo = FakeSavedContentRepository()
        service = ListSavedContentService(saved_content_repository=repo)
        org_id, user_id = uuid4(), uuid4()
        for _ in range(3):
            await repo.add(_saved(user_id=user_id, organization_id=org_id))

        result = await service.list_saved(
            ListSavedContentInput(organization_id=org_id, user_id=user_id, limit=2)
        )
        assert len(result.items) == 2
        assert result.next_cursor is not None

    async def test_no_next_cursor_when_everything_fits_on_one_page(self) -> None:
        repo = FakeSavedContentRepository()
        service = ListSavedContentService(saved_content_repository=repo)
        org_id, user_id = uuid4(), uuid4()
        await repo.add(_saved(user_id=user_id, organization_id=org_id))

        result = await service.list_saved(
            ListSavedContentInput(organization_id=org_id, user_id=user_id)
        )
        assert result.next_cursor is None

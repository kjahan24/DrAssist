"""Unit tests for `DeleteCommentService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community_comments.application.dto import DeleteCommentInput
from app.modules.community_comments.application.services.delete_comment_service import (
    DeleteCommentService,
)
from app.modules.community_comments.domain.entities import CommunityComment
from app.modules.community_comments.domain.enums import CommentStatus, CommentTargetType
from app.modules.community_comments.domain.exceptions import (
    CommentNotFoundError,
    InsufficientCommentRoleError,
)
from app.modules.community_comments.domain.value_objects import CommentBody
from tests.unit.modules.community_comments.application.fakes import (
    FakeCommunityCommentRepository,
    FakeCommunityQueryPort,
    FakeUnitOfWork,
    make_member_summary,
)


def _seeded() -> (
    tuple[
        DeleteCommentService, FakeCommunityCommentRepository, FakeCommunityQueryPort, FakeUnitOfWork
    ]
):
    comments = FakeCommunityCommentRepository()
    communities = FakeCommunityQueryPort()
    uow = FakeUnitOfWork()
    service = DeleteCommentService(
        comment_repository=comments, community_query_port=communities, unit_of_work=uow
    )
    return service, comments, communities, uow


async def _seed_comment(
    comments: FakeCommunityCommentRepository, *, author_id: object, community_id: object
) -> CommunityComment:
    comment = CommunityComment.create(
        target_type=CommentTargetType.POST,
        target_id=uuid4(),
        community_id=community_id,  # type: ignore[arg-type]
        organization_id=uuid4(),
        topic_id=None,
        author_id=author_id,  # type: ignore[arg-type]
        body=CommentBody("Body."),
    )
    await comments.add(comment)
    return comment


class TestDeleteComment:
    async def test_sets_status_to_deleted(self) -> None:
        service, comments, communities, _ = _seeded()
        author_id, community_id = uuid4(), uuid4()
        comment = await _seed_comment(comments, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        await service.execute(DeleteCommentInput(comment_id=comment.id, acting_user_id=author_id))
        stored = await comments.get_by_id(comment.id)
        assert stored is not None
        assert stored.status is CommentStatus.DELETED

    async def test_plain_member_cannot_delete_another_authors_comment(self) -> None:
        service, comments, communities, _ = _seeded()
        author_id, other_id, community_id = uuid4(), uuid4(), uuid4()
        comment = await _seed_comment(comments, author_id=author_id, community_id=community_id)
        communities.add_membership(make_member_summary(community_id=community_id, user_id=other_id))

        with pytest.raises(InsufficientCommentRoleError):
            await service.execute(
                DeleteCommentInput(comment_id=comment.id, acting_user_id=other_id)
            )

    async def test_unknown_comment_raises(self) -> None:
        service, _, _, _ = _seeded()
        with pytest.raises(CommentNotFoundError):
            await service.execute(DeleteCommentInput(comment_id=uuid4(), acting_user_id=uuid4()))

    async def test_commits_the_unit_of_work(self) -> None:
        service, comments, communities, uow = _seeded()
        author_id, community_id = uuid4(), uuid4()
        comment = await _seed_comment(comments, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        await service.execute(DeleteCommentInput(comment_id=comment.id, acting_user_id=author_id))
        assert uow.committed is True

"""Unit tests for `ManagePostAttachmentsService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityRole
from app.modules.community_posts.application.dto import (
    AddPostAttachmentInput,
    RemovePostAttachmentInput,
)
from app.modules.community_posts.application.services.manage_post_attachments_service import (
    ManagePostAttachmentsService,
)
from app.modules.community_posts.domain.entities import CommunityPost
from app.modules.community_posts.domain.events import CommunityPostAttachmentAdded
from app.modules.community_posts.domain.exceptions import (
    DocumentNotFoundForPostError,
    DuplicatePostAttachmentError,
    InsufficientPostRoleError,
    PostAttachmentNotFoundError,
    PostNotFoundError,
)
from app.modules.community_posts.domain.value_objects import PostTitle
from tests.unit.modules.community_posts.application.fakes import (
    FakeCommunityPostAttachmentRepository,
    FakeCommunityPostRepository,
    FakeCommunityQueryPort,
    FakeDocumentQueryPort,
    FakeUnitOfWork,
    make_community_summary,
    make_member_summary,
)


def _seeded() -> (
    tuple[
        ManagePostAttachmentsService,
        FakeCommunityPostRepository,
        FakeCommunityPostAttachmentRepository,
        FakeCommunityQueryPort,
        FakeDocumentQueryPort,
        FakeUnitOfWork,
    ]
):
    posts = FakeCommunityPostRepository()
    attachments = FakeCommunityPostAttachmentRepository()
    communities = FakeCommunityQueryPort()
    documents = FakeDocumentQueryPort()
    uow = FakeUnitOfWork()
    service = ManagePostAttachmentsService(
        post_attachment_repository=attachments,
        post_repository=posts,
        community_query_port=communities,
        document_query_port=documents,
        unit_of_work=uow,
    )
    return service, posts, attachments, communities, documents, uow


async def _seed_post(
    posts: FakeCommunityPostRepository, communities: FakeCommunityQueryPort
) -> CommunityPost:
    post = CommunityPost.create(
        community_id=uuid4(),
        organization_id=uuid4(),
        author_id=uuid4(),
        title=PostTitle("Title"),
        body="Body",
    )
    await posts.add(post)
    communities.add_community(make_community_summary(community_id=post.community_id))
    return post


class TestAddAttachment:
    async def test_author_adds_an_attachment(self) -> None:
        service, posts, attachments, communities, documents, _ = _seeded()
        post = await _seed_post(posts, communities)
        document_id = uuid4()
        documents.add_document(document_id)

        summary = await service.add_attachment(
            AddPostAttachmentInput(
                post_id=post.id, acting_user_id=post.author_id, document_id=document_id
            )
        )
        assert summary.document_id == document_id
        assert len(await attachments.list_by_post(post.id)) == 1

    async def test_plain_member_cannot_add_attachment_to_someone_elses_post(self) -> None:
        service, posts, _, communities, documents, _ = _seeded()
        post = await _seed_post(posts, communities)
        document_id = uuid4()
        documents.add_document(document_id)
        member_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=post.community_id, user_id=member_id, role=CommunityRole.MEMBER
            )
        )

        with pytest.raises(InsufficientPostRoleError):
            await service.add_attachment(
                AddPostAttachmentInput(
                    post_id=post.id, acting_user_id=member_id, document_id=document_id
                )
            )

    async def test_unknown_post_raises(self) -> None:
        service, _, _, _, documents, _ = _seeded()
        document_id = uuid4()
        documents.add_document(document_id)
        with pytest.raises(PostNotFoundError):
            await service.add_attachment(
                AddPostAttachmentInput(
                    post_id=uuid4(), acting_user_id=uuid4(), document_id=document_id
                )
            )

    async def test_unknown_document_raises(self) -> None:
        service, posts, _, communities, _, _ = _seeded()
        post = await _seed_post(posts, communities)

        with pytest.raises(DocumentNotFoundForPostError):
            await service.add_attachment(
                AddPostAttachmentInput(
                    post_id=post.id, acting_user_id=post.author_id, document_id=uuid4()
                )
            )

    async def test_duplicate_attachment_raises(self) -> None:
        service, posts, _, communities, documents, _ = _seeded()
        post = await _seed_post(posts, communities)
        document_id = uuid4()
        documents.add_document(document_id)
        await service.add_attachment(
            AddPostAttachmentInput(
                post_id=post.id, acting_user_id=post.author_id, document_id=document_id
            )
        )

        with pytest.raises(DuplicatePostAttachmentError):
            await service.add_attachment(
                AddPostAttachmentInput(
                    post_id=post.id, acting_user_id=post.author_id, document_id=document_id
                )
            )

    async def test_commits_and_publishes_event(self) -> None:
        service, posts, _, communities, documents, uow = _seeded()
        post = await _seed_post(posts, communities)
        document_id = uuid4()
        documents.add_document(document_id)

        await service.add_attachment(
            AddPostAttachmentInput(
                post_id=post.id, acting_user_id=post.author_id, document_id=document_id
            )
        )
        assert uow.committed is True
        assert any(isinstance(e, CommunityPostAttachmentAdded) for e in uow.published_events)

    async def test_the_same_document_can_be_attached_to_two_different_posts(self) -> None:
        service, posts, _, communities, documents, _ = _seeded()
        first_post = await _seed_post(posts, communities)
        second_post = await _seed_post(posts, communities)
        document_id = uuid4()
        documents.add_document(document_id)

        await service.add_attachment(
            AddPostAttachmentInput(
                post_id=first_post.id, acting_user_id=first_post.author_id, document_id=document_id
            )
        )
        await service.add_attachment(
            AddPostAttachmentInput(
                post_id=second_post.id,
                acting_user_id=second_post.author_id,
                document_id=document_id,
            )
        )

        assert len(await service.list_attachments(first_post.id)) == 1
        assert len(await service.list_attachments(second_post.id)) == 1


class TestListAttachments:
    async def test_lists_added_attachments(self) -> None:
        service, posts, _, communities, documents, _ = _seeded()
        post = await _seed_post(posts, communities)
        document_id = uuid4()
        documents.add_document(document_id)
        await service.add_attachment(
            AddPostAttachmentInput(
                post_id=post.id, acting_user_id=post.author_id, document_id=document_id
            )
        )

        result = await service.list_attachments(post.id)
        assert [a.document_id for a in result] == [document_id]

    async def test_returns_empty_for_a_post_with_no_attachments(self) -> None:
        service, posts, _, communities, _, _ = _seeded()
        post = await _seed_post(posts, communities)

        assert await service.list_attachments(post.id) == []


class TestRemoveAttachment:
    async def test_author_removes_an_attachment(self) -> None:
        service, posts, _, communities, documents, _ = _seeded()
        post = await _seed_post(posts, communities)
        document_id = uuid4()
        documents.add_document(document_id)
        added = await service.add_attachment(
            AddPostAttachmentInput(
                post_id=post.id, acting_user_id=post.author_id, document_id=document_id
            )
        )

        await service.remove_attachment(
            RemovePostAttachmentInput(
                post_id=post.id, acting_user_id=post.author_id, attachment_id=added.attachment_id
            )
        )
        assert await service.list_attachments(post.id) == []

    async def test_moderator_removes_an_attachment_from_someone_elses_post(self) -> None:
        service, posts, _, communities, documents, _ = _seeded()
        post = await _seed_post(posts, communities)
        document_id = uuid4()
        documents.add_document(document_id)
        added = await service.add_attachment(
            AddPostAttachmentInput(
                post_id=post.id, acting_user_id=post.author_id, document_id=document_id
            )
        )
        moderator_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=post.community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )

        await service.remove_attachment(
            RemovePostAttachmentInput(
                post_id=post.id, acting_user_id=moderator_id, attachment_id=added.attachment_id
            )
        )
        assert await service.list_attachments(post.id) == []

    async def test_plain_member_cannot_remove_attachment_from_someone_elses_post(self) -> None:
        service, posts, _, communities, documents, _ = _seeded()
        post = await _seed_post(posts, communities)
        document_id = uuid4()
        documents.add_document(document_id)
        added = await service.add_attachment(
            AddPostAttachmentInput(
                post_id=post.id, acting_user_id=post.author_id, document_id=document_id
            )
        )
        member_id = uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=post.community_id, user_id=member_id, role=CommunityRole.MEMBER
            )
        )

        with pytest.raises(InsufficientPostRoleError):
            await service.remove_attachment(
                RemovePostAttachmentInput(
                    post_id=post.id, acting_user_id=member_id, attachment_id=added.attachment_id
                )
            )

    async def test_unknown_attachment_raises(self) -> None:
        service, posts, _, communities, _, _ = _seeded()
        post = await _seed_post(posts, communities)

        with pytest.raises(PostAttachmentNotFoundError):
            await service.remove_attachment(
                RemovePostAttachmentInput(
                    post_id=post.id, acting_user_id=post.author_id, attachment_id=uuid4()
                )
            )

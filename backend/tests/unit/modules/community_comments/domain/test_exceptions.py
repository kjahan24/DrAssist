"""Tests for the Community Comments module's domain exceptions."""

from uuid import uuid4

from app.modules.community_comments.domain.exceptions import (
    CommentAlreadyArchivedError,
    CommentAlreadyDeletedError,
    CommentAlreadyPublishedError,
    CommentAttachmentNotFoundError,
    CommentBodyRequiredError,
    CommentBodyTooLongError,
    CommentCannotBeRestoredError,
    CommentMembershipRequiredError,
    CommentNotFoundError,
    CommentNotViewableError,
    DocumentNotFoundForCommentError,
    DuplicateCommentAttachmentError,
    InsufficientCommentRoleError,
    MaxCommentDepthExceededError,
    ParentCommentNotAcceptingRepliesError,
    ParentCommentNotFoundError,
    TargetNotAcceptingCommentsError,
    TargetNotFoundForCommentError,
    TargetNotViewableForCommentError,
)
from app.shared.domain.exceptions import DomainError


class TestCommentBodyRequiredError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommentBodyRequiredError(), DomainError)

    def test_message(self) -> None:
        assert "blank" in str(CommentBodyRequiredError())


class TestCommentBodyTooLongError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommentBodyTooLongError(10000), DomainError)

    def test_message_includes_max_length(self) -> None:
        error = CommentBodyTooLongError(10000)
        assert "10000" in str(error)
        assert error.max_length == 10000


class TestCommentNotFoundError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommentNotFoundError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        comment_id = uuid4()
        error = CommentNotFoundError(comment_id)
        assert str(comment_id) in str(error)
        assert error.comment_id == comment_id


class TestCommentAlreadyPublishedError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommentAlreadyPublishedError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        comment_id = uuid4()
        error = CommentAlreadyPublishedError(comment_id)
        assert str(comment_id) in str(error)
        assert error.comment_id == comment_id


class TestCommentAlreadyArchivedError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommentAlreadyArchivedError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        comment_id = uuid4()
        error = CommentAlreadyArchivedError(comment_id)
        assert str(comment_id) in str(error)
        assert error.comment_id == comment_id


class TestCommentAlreadyDeletedError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommentAlreadyDeletedError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        comment_id = uuid4()
        error = CommentAlreadyDeletedError(comment_id)
        assert str(comment_id) in str(error)
        assert error.comment_id == comment_id


class TestCommentCannotBeRestoredError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommentCannotBeRestoredError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        comment_id = uuid4()
        error = CommentCannotBeRestoredError(comment_id)
        assert str(comment_id) in str(error)
        assert error.comment_id == comment_id


class TestTargetNotFoundForCommentError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(TargetNotFoundForCommentError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        target_id = uuid4()
        error = TargetNotFoundForCommentError(target_id)
        assert str(target_id) in str(error)
        assert error.target_id == target_id


class TestTargetNotAcceptingCommentsError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(TargetNotAcceptingCommentsError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        target_id = uuid4()
        error = TargetNotAcceptingCommentsError(target_id)
        assert str(target_id) in str(error)
        assert error.target_id == target_id


class TestTargetNotViewableForCommentError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(TargetNotViewableForCommentError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        target_id = uuid4()
        error = TargetNotViewableForCommentError(target_id)
        assert str(target_id) in str(error)
        assert error.target_id == target_id


class TestParentCommentNotFoundError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(ParentCommentNotFoundError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        parent_id = uuid4()
        error = ParentCommentNotFoundError(parent_id)
        assert str(parent_id) in str(error)
        assert error.parent_comment_id == parent_id


class TestParentCommentNotAcceptingRepliesError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(ParentCommentNotAcceptingRepliesError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        parent_id = uuid4()
        error = ParentCommentNotAcceptingRepliesError(parent_id)
        assert str(parent_id) in str(error)
        assert error.parent_comment_id == parent_id


class TestMaxCommentDepthExceededError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(MaxCommentDepthExceededError(uuid4(), 5), DomainError)

    def test_message_includes_id_and_max_depth(self) -> None:
        parent_id = uuid4()
        error = MaxCommentDepthExceededError(parent_id, 5)
        assert str(parent_id) in str(error)
        assert "5" in str(error)
        assert error.parent_comment_id == parent_id
        assert error.max_depth == 5


class TestDocumentNotFoundForCommentError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(DocumentNotFoundForCommentError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        document_id = uuid4()
        error = DocumentNotFoundForCommentError(document_id)
        assert str(document_id) in str(error)
        assert error.document_id == document_id


class TestInsufficientCommentRoleError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(InsufficientCommentRoleError(uuid4(), uuid4()), DomainError)

    def test_message_includes_both_ids(self) -> None:
        community_id, user_id = uuid4(), uuid4()
        error = InsufficientCommentRoleError(community_id, user_id)
        assert str(community_id) in str(error)
        assert str(user_id) in str(error)


class TestCommentMembershipRequiredError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommentMembershipRequiredError(uuid4(), uuid4()), DomainError)

    def test_message_includes_both_ids(self) -> None:
        community_id, user_id = uuid4(), uuid4()
        error = CommentMembershipRequiredError(community_id, user_id)
        assert str(community_id) in str(error)
        assert str(user_id) in str(error)


class TestCommentNotViewableError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommentNotViewableError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        comment_id = uuid4()
        error = CommentNotViewableError(comment_id)
        assert str(comment_id) in str(error)
        assert error.comment_id == comment_id


class TestDuplicateCommentAttachmentError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(DuplicateCommentAttachmentError(uuid4(), uuid4()), DomainError)

    def test_message_includes_both_ids(self) -> None:
        comment_id, document_id = uuid4(), uuid4()
        error = DuplicateCommentAttachmentError(comment_id, document_id)
        assert str(comment_id) in str(error)
        assert str(document_id) in str(error)


class TestCommentAttachmentNotFoundError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommentAttachmentNotFoundError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        attachment_id = uuid4()
        error = CommentAttachmentNotFoundError(attachment_id)
        assert str(attachment_id) in str(error)
        assert error.attachment_id == attachment_id

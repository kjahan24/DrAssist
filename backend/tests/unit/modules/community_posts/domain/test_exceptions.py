"""Tests for the Community Posts module's domain exceptions."""

from uuid import uuid4

from app.modules.community_posts.domain.exceptions import (
    CommunityNotFoundForPostError,
    DocumentNotFoundForPostError,
    DuplicatePostAttachmentError,
    DuplicatePostSlugError,
    DuplicatePostTagError,
    DuplicatePostTopicError,
    InsufficientPostRoleError,
    InvalidPostSlugError,
    PostAlreadyArchivedError,
    PostAlreadyPublishedError,
    PostAttachmentNotFoundError,
    PostBodyRequiredError,
    PostExcerptRequiredError,
    PostExcerptTooLongError,
    PostMembershipRequiredError,
    PostNotFoundError,
    PostNotViewableError,
    PostTagNotFoundError,
    PostTagRequiredError,
    PostTagTooLongError,
    PostTitleRequiredError,
    PostTitleTooLongError,
    PostTopicNotFoundError,
    TopicNotFoundForPostError,
)
from app.shared.domain.exceptions import DomainError


class TestPostTitleRequiredError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(PostTitleRequiredError(), DomainError)

    def test_message(self) -> None:
        assert "blank" in str(PostTitleRequiredError())


class TestPostTitleTooLongError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(PostTitleTooLongError(300), DomainError)

    def test_message_includes_max_length(self) -> None:
        error = PostTitleTooLongError(300)
        assert "300" in str(error)
        assert error.max_length == 300


class TestInvalidPostSlugError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(InvalidPostSlugError("bad slug"), DomainError)

    def test_message_includes_the_bad_value(self) -> None:
        error = InvalidPostSlugError("Bad Slug!")
        assert "Bad Slug!" in str(error)
        assert error.value == "Bad Slug!"


class TestDuplicatePostSlugError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(DuplicatePostSlugError(uuid4(), "oncology-tips"), DomainError)

    def test_message_includes_community_id_and_slug(self) -> None:
        community_id = uuid4()
        error = DuplicatePostSlugError(community_id, "oncology-tips")
        assert str(community_id) in str(error)
        assert "oncology-tips" in str(error)
        assert error.slug == "oncology-tips"


class TestPostExcerptRequiredError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(PostExcerptRequiredError(), DomainError)

    def test_message(self) -> None:
        assert "blank" in str(PostExcerptRequiredError())


class TestPostExcerptTooLongError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(PostExcerptTooLongError(500), DomainError)

    def test_message_includes_max_length(self) -> None:
        error = PostExcerptTooLongError(500)
        assert "500" in str(error)
        assert error.max_length == 500


class TestPostBodyRequiredError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(PostBodyRequiredError(), DomainError)

    def test_message(self) -> None:
        assert "blank" in str(PostBodyRequiredError())


class TestPostNotFoundError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(PostNotFoundError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        post_id = uuid4()
        error = PostNotFoundError(post_id)
        assert str(post_id) in str(error)
        assert error.post_id == post_id


class TestPostAlreadyPublishedError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(PostAlreadyPublishedError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        post_id = uuid4()
        error = PostAlreadyPublishedError(post_id)
        assert str(post_id) in str(error)
        assert error.post_id == post_id


class TestPostAlreadyArchivedError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(PostAlreadyArchivedError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        post_id = uuid4()
        error = PostAlreadyArchivedError(post_id)
        assert str(post_id) in str(error)
        assert error.post_id == post_id


class TestCommunityNotFoundForPostError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommunityNotFoundForPostError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        community_id = uuid4()
        error = CommunityNotFoundForPostError(community_id)
        assert str(community_id) in str(error)
        assert error.community_id == community_id


class TestTopicNotFoundForPostError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(TopicNotFoundForPostError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        topic_id = uuid4()
        error = TopicNotFoundForPostError(topic_id)
        assert str(topic_id) in str(error)
        assert error.topic_id == topic_id


class TestDocumentNotFoundForPostError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(DocumentNotFoundForPostError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        document_id = uuid4()
        error = DocumentNotFoundForPostError(document_id)
        assert str(document_id) in str(error)
        assert error.document_id == document_id


class TestInsufficientPostRoleError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(InsufficientPostRoleError(uuid4(), uuid4()), DomainError)

    def test_message_includes_both_ids(self) -> None:
        community_id, user_id = uuid4(), uuid4()
        error = InsufficientPostRoleError(community_id, user_id)
        assert str(community_id) in str(error)
        assert str(user_id) in str(error)


class TestPostMembershipRequiredError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(PostMembershipRequiredError(uuid4(), uuid4()), DomainError)

    def test_message_includes_both_ids(self) -> None:
        community_id, user_id = uuid4(), uuid4()
        error = PostMembershipRequiredError(community_id, user_id)
        assert str(community_id) in str(error)
        assert str(user_id) in str(error)


class TestPostNotViewableError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(PostNotViewableError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        post_id = uuid4()
        error = PostNotViewableError(post_id)
        assert str(post_id) in str(error)
        assert error.post_id == post_id


class TestPostTagRequiredError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(PostTagRequiredError(), DomainError)

    def test_message(self) -> None:
        assert "blank" in str(PostTagRequiredError())


class TestPostTagTooLongError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(PostTagTooLongError(50), DomainError)

    def test_message_includes_max_length(self) -> None:
        error = PostTagTooLongError(50)
        assert "50" in str(error)
        assert error.max_length == 50


class TestDuplicatePostTagError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(DuplicatePostTagError(uuid4(), "diabetes"), DomainError)

    def test_message_includes_id_and_tag(self) -> None:
        post_id = uuid4()
        error = DuplicatePostTagError(post_id, "diabetes")
        assert str(post_id) in str(error)
        assert "diabetes" in str(error)


class TestPostTagNotFoundError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(PostTagNotFoundError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        tag_id = uuid4()
        error = PostTagNotFoundError(tag_id)
        assert str(tag_id) in str(error)
        assert error.tag_id == tag_id


class TestDuplicatePostTopicError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(DuplicatePostTopicError(uuid4(), uuid4()), DomainError)

    def test_message_includes_both_ids(self) -> None:
        post_id, topic_id = uuid4(), uuid4()
        error = DuplicatePostTopicError(post_id, topic_id)
        assert str(post_id) in str(error)
        assert str(topic_id) in str(error)


class TestPostTopicNotFoundError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(PostTopicNotFoundError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        post_topic_id = uuid4()
        error = PostTopicNotFoundError(post_topic_id)
        assert str(post_topic_id) in str(error)
        assert error.post_topic_id == post_topic_id


class TestDuplicatePostAttachmentError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(DuplicatePostAttachmentError(uuid4(), uuid4()), DomainError)

    def test_message_includes_both_ids(self) -> None:
        post_id, document_id = uuid4(), uuid4()
        error = DuplicatePostAttachmentError(post_id, document_id)
        assert str(post_id) in str(error)
        assert str(document_id) in str(error)


class TestPostAttachmentNotFoundError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(PostAttachmentNotFoundError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        attachment_id = uuid4()
        error = PostAttachmentNotFoundError(attachment_id)
        assert str(attachment_id) in str(error)
        assert error.attachment_id == attachment_id

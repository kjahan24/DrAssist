"""Domain exceptions for the Community Posts module.

Naming follows the codebase-wide convention `app.middlewares.error_handler
._map_domain_error` relies on: a name containing "NotFound" maps to 404; a
name containing "Duplicate"/"AlreadyExists"/"Transition"/"Immutable"/
"Inactive" maps to 409; everything else maps to 422 (well-formed request,
semantically invalid). See that module's own docstring for the full
heuristic.
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class PostTitleRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("Post title must not be blank.")


class PostTitleTooLongError(DomainError):
    def __init__(self, max_length: int) -> None:
        self.max_length = max_length
        super().__init__(f"Post title must be at most {max_length} characters.")


class InvalidPostSlugError(DomainError):
    def __init__(self, value: str) -> None:
        self.value = value
        super().__init__(f"Invalid post slug: {value!r}.")


class DuplicatePostSlugError(DomainError):
    def __init__(self, community_id: UUID, slug: str) -> None:
        self.community_id = community_id
        self.slug = slug
        super().__init__(f"A post with slug {slug!r} already exists in community {community_id}.")


class PostExcerptRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("Post excerpt must not be blank.")


class PostExcerptTooLongError(DomainError):
    def __init__(self, max_length: int) -> None:
        self.max_length = max_length
        super().__init__(f"Post excerpt must be at most {max_length} characters.")


class PostBodyRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("Post body must not be blank.")


class PostNotFoundError(DomainError):
    def __init__(self, post_id: UUID) -> None:
        self.post_id = post_id
        super().__init__(f"No post found with id {post_id}.")


class PostAlreadyPublishedError(DomainError):
    def __init__(self, post_id: UUID) -> None:
        self.post_id = post_id
        super().__init__(f"Post {post_id} is already published.")


class PostAlreadyArchivedError(DomainError):
    def __init__(self, post_id: UUID) -> None:
        self.post_id = post_id
        super().__init__(f"Post {post_id} is already archived.")


class CommunityNotFoundForPostError(DomainError):
    def __init__(self, community_id: UUID) -> None:
        self.community_id = community_id
        super().__init__(f"No community found with id {community_id}.")


class TopicNotFoundForPostError(DomainError):
    def __init__(self, topic_id: UUID) -> None:
        self.topic_id = topic_id
        super().__init__(f"No topic found with id {topic_id}.")


class DocumentNotFoundForPostError(DomainError):
    def __init__(self, document_id: UUID) -> None:
        self.document_id = document_id
        super().__init__(f"No document found with id {document_id}.")


class InsufficientPostRoleError(DomainError):
    def __init__(self, community_id: UUID, user_id: UUID) -> None:
        self.community_id = community_id
        self.user_id = user_id
        super().__init__(
            f"User {user_id} is not the post's author and does not hold a "
            f"moderating role in community {community_id}."
        )


class PostMembershipRequiredError(DomainError):
    def __init__(self, community_id: UUID, user_id: UUID) -> None:
        self.community_id = community_id
        self.user_id = user_id
        super().__init__(f"User {user_id} has no membership in community {community_id}.")


class PostNotViewableError(DomainError):
    def __init__(self, post_id: UUID) -> None:
        self.post_id = post_id
        super().__init__(f"Post {post_id} is not viewable by this caller.")


class PostTagRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("Post tag must not be blank.")


class PostTagTooLongError(DomainError):
    def __init__(self, max_length: int) -> None:
        self.max_length = max_length
        super().__init__(f"Post tag must be at most {max_length} characters.")


class DuplicatePostTagError(DomainError):
    def __init__(self, post_id: UUID, tag: str) -> None:
        self.post_id = post_id
        self.tag = tag
        super().__init__(f"Post {post_id} already has tag {tag!r}.")


class PostTagNotFoundError(DomainError):
    def __init__(self, tag_id: UUID) -> None:
        self.tag_id = tag_id
        super().__init__(f"No post tag found with id {tag_id}.")


class DuplicatePostTopicError(DomainError):
    def __init__(self, post_id: UUID, topic_id: UUID) -> None:
        self.post_id = post_id
        self.topic_id = topic_id
        super().__init__(f"Post {post_id} is already assigned to topic {topic_id}.")


class PostTopicNotFoundError(DomainError):
    def __init__(self, post_topic_id: UUID) -> None:
        self.post_topic_id = post_topic_id
        super().__init__(f"No post-topic assignment found with id {post_topic_id}.")


class DuplicatePostAttachmentError(DomainError):
    def __init__(self, post_id: UUID, document_id: UUID) -> None:
        self.post_id = post_id
        self.document_id = document_id
        super().__init__(f"Post {post_id} already has attachment {document_id}.")


class PostAttachmentNotFoundError(DomainError):
    def __init__(self, attachment_id: UUID) -> None:
        self.attachment_id = attachment_id
        super().__init__(f"No post attachment found with id {attachment_id}.")

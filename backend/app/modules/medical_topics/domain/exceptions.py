"""Domain exceptions for the Medical Topics module.

Naming follows the codebase-wide convention `app.middlewares.error_handler
._map_domain_error` relies on: a name containing "NotFound" maps to 404; a
name containing "Duplicate"/"AlreadyExists"/"Transition"/"Immutable"/
"Inactive" maps to 409; everything else maps to 422 (well-formed request,
semantically invalid). See that module's own docstring for the full
heuristic.
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class TopicNameRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("Topic name must not be blank.")


class TopicNameTooLongError(DomainError):
    def __init__(self, max_length: int) -> None:
        self.max_length = max_length
        super().__init__(f"Topic name must be at most {max_length} characters.")


class InvalidTopicSlugError(DomainError):
    def __init__(self, value: str) -> None:
        self.value = value
        super().__init__(f"Invalid topic slug: {value!r}.")


class DuplicateTopicSlugError(DomainError):
    def __init__(self, slug: str) -> None:
        self.slug = slug
        super().__init__(f"A topic with slug {slug!r} already exists.")


class TopicDescriptionRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("Topic description must not be blank.")


class TopicDescriptionTooLongError(DomainError):
    def __init__(self, max_length: int) -> None:
        self.max_length = max_length
        super().__init__(f"Topic description must be at most {max_length} characters.")


class InvalidTopicColorError(DomainError):
    def __init__(self, value: str) -> None:
        self.value = value
        super().__init__(f"Invalid topic color: {value!r} (expected a #RRGGBB hex code).")


class TopicNotFoundError(DomainError):
    def __init__(self, topic_id: UUID) -> None:
        self.topic_id = topic_id
        super().__init__(f"No topic found with id {topic_id}.")


class ParentTopicNotFoundError(DomainError):
    def __init__(self, parent_id: UUID) -> None:
        self.parent_id = parent_id
        super().__init__(f"No parent topic found with id {parent_id}.")


class TopicCannotBeOwnParentError(DomainError):
    def __init__(self, topic_id: UUID) -> None:
        self.topic_id = topic_id
        super().__init__(f"Topic {topic_id} cannot be its own parent.")


class CircularTopicHierarchyError(DomainError):
    def __init__(self, topic_id: UUID, parent_id: UUID) -> None:
        self.topic_id = topic_id
        self.parent_id = parent_id
        super().__init__(
            f"Assigning parent {parent_id} to topic {topic_id} would create a circular hierarchy."
        )


class NegativeTopicScoreError(DomainError):
    def __init__(self, field: str) -> None:
        self.field = field
        super().__init__(f"Topic {field} must not be negative.")


class TopicSpecialtyNameRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("Topic specialty name must not be blank.")


class TopicSpecialtyNameTooLongError(DomainError):
    def __init__(self, max_length: int) -> None:
        self.max_length = max_length
        super().__init__(f"Topic specialty name must be at most {max_length} characters.")


class DuplicateTopicSpecialtyNameError(DomainError):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"A topic specialty named {name!r} already exists.")


class TopicSpecialtyNotFoundError(DomainError):
    def __init__(self, specialty_id: UUID) -> None:
        self.specialty_id = specialty_id
        super().__init__(f"No topic specialty found with id {specialty_id}.")


class TopicAlreadyFollowedError(DomainError):
    def __init__(self, topic_id: UUID, user_id: UUID) -> None:
        self.topic_id = topic_id
        self.user_id = user_id
        super().__init__(f"User {user_id} is already following topic {topic_id}.")


class TopicNotFollowedError(DomainError):
    def __init__(self, topic_id: UUID, user_id: UUID) -> None:
        self.topic_id = topic_id
        self.user_id = user_id
        super().__init__(f"User {user_id} is not following topic {topic_id}.")


class DuplicateTopicAliasError(DomainError):
    def __init__(self, topic_id: UUID, alias: str) -> None:
        self.topic_id = topic_id
        self.alias = alias
        super().__init__(f"Topic {topic_id} already has alias {alias!r}.")


class TopicAliasNotFoundError(DomainError):
    def __init__(self, alias_id: UUID) -> None:
        self.alias_id = alias_id
        super().__init__(f"No topic alias found with id {alias_id}.")


class TopicCannotRelateToItselfError(DomainError):
    def __init__(self, topic_id: UUID) -> None:
        self.topic_id = topic_id
        super().__init__(f"Topic {topic_id} cannot be related to itself.")


class DuplicateTopicRelationError(DomainError):
    def __init__(self, topic_id: UUID, related_topic_id: UUID) -> None:
        self.topic_id = topic_id
        self.related_topic_id = related_topic_id
        super().__init__(f"Topic {topic_id} is already related to topic {related_topic_id}.")


class TopicRelationNotFoundError(DomainError):
    def __init__(self, relation_id: UUID) -> None:
        self.relation_id = relation_id
        super().__init__(f"No topic relation found with id {relation_id}.")

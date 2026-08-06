"""Tests for the Medical Topics module's domain exceptions."""

from uuid import uuid4

from app.modules.medical_topics.domain.exceptions import (
    CircularTopicHierarchyError,
    DuplicateTopicAliasError,
    DuplicateTopicRelationError,
    DuplicateTopicSlugError,
    DuplicateTopicSpecialtyNameError,
    InvalidTopicColorError,
    InvalidTopicSlugError,
    NegativeTopicScoreError,
    ParentTopicNotFoundError,
    TopicAliasNotFoundError,
    TopicAlreadyFollowedError,
    TopicCannotBeOwnParentError,
    TopicCannotRelateToItselfError,
    TopicDescriptionRequiredError,
    TopicDescriptionTooLongError,
    TopicNameRequiredError,
    TopicNameTooLongError,
    TopicNotFollowedError,
    TopicNotFoundError,
    TopicRelationNotFoundError,
    TopicSpecialtyNameRequiredError,
    TopicSpecialtyNameTooLongError,
    TopicSpecialtyNotFoundError,
)
from app.shared.domain.exceptions import DomainError


class TestTopicNameRequiredError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(TopicNameRequiredError(), DomainError)

    def test_message(self) -> None:
        assert "blank" in str(TopicNameRequiredError())


class TestTopicNameTooLongError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(TopicNameTooLongError(200), DomainError)

    def test_message_includes_max_length(self) -> None:
        error = TopicNameTooLongError(200)
        assert "200" in str(error)
        assert error.max_length == 200


class TestInvalidTopicSlugError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(InvalidTopicSlugError("bad slug"), DomainError)

    def test_message_includes_the_bad_value(self) -> None:
        error = InvalidTopicSlugError("Bad Slug!")
        assert "Bad Slug!" in str(error)
        assert error.value == "Bad Slug!"


class TestDuplicateTopicSlugError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(DuplicateTopicSlugError("oncology"), DomainError)

    def test_message_includes_slug(self) -> None:
        error = DuplicateTopicSlugError("oncology")
        assert "oncology" in str(error)
        assert error.slug == "oncology"


class TestTopicDescriptionRequiredError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(TopicDescriptionRequiredError(), DomainError)

    def test_message(self) -> None:
        assert "blank" in str(TopicDescriptionRequiredError())


class TestTopicDescriptionTooLongError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(TopicDescriptionTooLongError(2000), DomainError)

    def test_message_includes_max_length(self) -> None:
        error = TopicDescriptionTooLongError(2000)
        assert "2000" in str(error)
        assert error.max_length == 2000


class TestInvalidTopicColorError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(InvalidTopicColorError("red"), DomainError)

    def test_message_includes_the_bad_value(self) -> None:
        error = InvalidTopicColorError("red")
        assert "red" in str(error)
        assert error.value == "red"


class TestTopicNotFoundError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(TopicNotFoundError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        topic_id = uuid4()
        error = TopicNotFoundError(topic_id)
        assert str(topic_id) in str(error)
        assert error.topic_id == topic_id


class TestParentTopicNotFoundError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(ParentTopicNotFoundError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        parent_id = uuid4()
        error = ParentTopicNotFoundError(parent_id)
        assert str(parent_id) in str(error)
        assert error.parent_id == parent_id


class TestTopicCannotBeOwnParentError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(TopicCannotBeOwnParentError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        topic_id = uuid4()
        error = TopicCannotBeOwnParentError(topic_id)
        assert str(topic_id) in str(error)
        assert error.topic_id == topic_id


class TestCircularTopicHierarchyError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CircularTopicHierarchyError(uuid4(), uuid4()), DomainError)

    def test_message_includes_both_ids(self) -> None:
        topic_id, parent_id = uuid4(), uuid4()
        error = CircularTopicHierarchyError(topic_id, parent_id)
        assert str(topic_id) in str(error)
        assert str(parent_id) in str(error)
        assert error.topic_id == topic_id
        assert error.parent_id == parent_id


class TestNegativeTopicScoreError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(NegativeTopicScoreError("trending_score"), DomainError)

    def test_message_includes_field(self) -> None:
        error = NegativeTopicScoreError("popularity_score")
        assert "popularity_score" in str(error)
        assert error.field == "popularity_score"


class TestTopicSpecialtyNameRequiredError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(TopicSpecialtyNameRequiredError(), DomainError)

    def test_message(self) -> None:
        assert "blank" in str(TopicSpecialtyNameRequiredError())


class TestTopicSpecialtyNameTooLongError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(TopicSpecialtyNameTooLongError(100), DomainError)

    def test_message_includes_max_length(self) -> None:
        error = TopicSpecialtyNameTooLongError(100)
        assert "100" in str(error)
        assert error.max_length == 100


class TestDuplicateTopicSpecialtyNameError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(DuplicateTopicSpecialtyNameError("Oncology"), DomainError)

    def test_message_includes_name(self) -> None:
        error = DuplicateTopicSpecialtyNameError("Oncology")
        assert "Oncology" in str(error)
        assert error.name == "Oncology"


class TestTopicSpecialtyNotFoundError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(TopicSpecialtyNotFoundError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        specialty_id = uuid4()
        error = TopicSpecialtyNotFoundError(specialty_id)
        assert str(specialty_id) in str(error)
        assert error.specialty_id == specialty_id


class TestTopicAlreadyFollowedError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(TopicAlreadyFollowedError(uuid4(), uuid4()), DomainError)

    def test_message_includes_both_ids(self) -> None:
        topic_id, user_id = uuid4(), uuid4()
        error = TopicAlreadyFollowedError(topic_id, user_id)
        assert str(topic_id) in str(error)
        assert str(user_id) in str(error)


class TestTopicNotFollowedError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(TopicNotFollowedError(uuid4(), uuid4()), DomainError)

    def test_message_includes_both_ids(self) -> None:
        topic_id, user_id = uuid4(), uuid4()
        error = TopicNotFollowedError(topic_id, user_id)
        assert str(topic_id) in str(error)
        assert str(user_id) in str(error)


class TestDuplicateTopicAliasError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(DuplicateTopicAliasError(uuid4(), "diabetes"), DomainError)

    def test_message_includes_id_and_alias(self) -> None:
        topic_id = uuid4()
        error = DuplicateTopicAliasError(topic_id, "diabetes")
        assert str(topic_id) in str(error)
        assert "diabetes" in str(error)


class TestTopicAliasNotFoundError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(TopicAliasNotFoundError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        alias_id = uuid4()
        error = TopicAliasNotFoundError(alias_id)
        assert str(alias_id) in str(error)
        assert error.alias_id == alias_id


class TestTopicCannotRelateToItselfError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(TopicCannotRelateToItselfError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        topic_id = uuid4()
        error = TopicCannotRelateToItselfError(topic_id)
        assert str(topic_id) in str(error)
        assert error.topic_id == topic_id


class TestDuplicateTopicRelationError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(DuplicateTopicRelationError(uuid4(), uuid4()), DomainError)

    def test_message_includes_both_ids(self) -> None:
        topic_id, related_topic_id = uuid4(), uuid4()
        error = DuplicateTopicRelationError(topic_id, related_topic_id)
        assert str(topic_id) in str(error)
        assert str(related_topic_id) in str(error)


class TestTopicRelationNotFoundError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(TopicRelationNotFoundError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        relation_id = uuid4()
        error = TopicRelationNotFoundError(relation_id)
        assert str(relation_id) in str(error)
        assert error.relation_id == relation_id

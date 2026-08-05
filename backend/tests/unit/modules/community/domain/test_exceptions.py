"""Tests for the Community module's domain exceptions."""

from uuid import uuid4

from app.modules.community.domain.exceptions import (
    CommunityDescriptionRequiredError,
    CommunityDescriptionTooLongError,
    CommunityMemberBlockedError,
    CommunityMembershipAlreadyExistsError,
    CommunityMembershipNotFoundError,
    CommunityNameRequiredError,
    CommunityNameTooLongError,
    CommunityNotFoundError,
    CommunityOwnerRequiredError,
    DuplicateCommunitySlugError,
    InsufficientCommunityRoleError,
    InvalidCommunitySlugError,
    PrivateCommunityJoinRequiresInviteError,
)
from app.shared.domain.exceptions import DomainError


class TestCommunityNameRequiredError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommunityNameRequiredError(), DomainError)

    def test_message(self) -> None:
        assert "blank" in str(CommunityNameRequiredError())


class TestCommunityNameTooLongError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommunityNameTooLongError(200), DomainError)

    def test_message_includes_max_length(self) -> None:
        error = CommunityNameTooLongError(200)
        assert "200" in str(error)
        assert error.max_length == 200


class TestInvalidCommunitySlugError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(InvalidCommunitySlugError("bad slug"), DomainError)

    def test_message_includes_the_bad_value(self) -> None:
        error = InvalidCommunitySlugError("Bad Slug!")
        assert "Bad Slug!" in str(error)
        assert error.value == "Bad Slug!"


class TestCommunityDescriptionRequiredError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommunityDescriptionRequiredError(), DomainError)

    def test_message(self) -> None:
        assert "blank" in str(CommunityDescriptionRequiredError())


class TestCommunityDescriptionTooLongError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommunityDescriptionTooLongError(2000), DomainError)

    def test_message_includes_max_length(self) -> None:
        error = CommunityDescriptionTooLongError(2000)
        assert "2000" in str(error)
        assert error.max_length == 2000


class TestDuplicateCommunitySlugError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(DuplicateCommunitySlugError("diabetes-support"), DomainError)

    def test_message_includes_slug(self) -> None:
        error = DuplicateCommunitySlugError("diabetes-support")
        assert "diabetes-support" in str(error)
        assert error.slug == "diabetes-support"


class TestCommunityNotFoundError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommunityNotFoundError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        community_id = uuid4()
        error = CommunityNotFoundError(community_id)
        assert str(community_id) in str(error)
        assert error.community_id == community_id


class TestCommunityMembershipNotFoundError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommunityMembershipNotFoundError(uuid4(), uuid4()), DomainError)

    def test_message_includes_both_ids(self) -> None:
        community_id, user_id = uuid4(), uuid4()
        error = CommunityMembershipNotFoundError(community_id, user_id)
        assert str(community_id) in str(error)
        assert str(user_id) in str(error)
        assert error.community_id == community_id
        assert error.user_id == user_id


class TestCommunityMembershipAlreadyExistsError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommunityMembershipAlreadyExistsError(uuid4(), uuid4()), DomainError)

    def test_message_includes_both_ids(self) -> None:
        community_id, user_id = uuid4(), uuid4()
        error = CommunityMembershipAlreadyExistsError(community_id, user_id)
        assert str(community_id) in str(error)
        assert str(user_id) in str(error)


class TestCommunityMemberBlockedError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommunityMemberBlockedError(uuid4(), uuid4()), DomainError)

    def test_message_includes_both_ids(self) -> None:
        community_id, user_id = uuid4(), uuid4()
        error = CommunityMemberBlockedError(community_id, user_id)
        assert str(community_id) in str(error)
        assert str(user_id) in str(error)


class TestPrivateCommunityJoinRequiresInviteError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(PrivateCommunityJoinRequiresInviteError(uuid4()), DomainError)

    def test_message_includes_community_id(self) -> None:
        community_id = uuid4()
        error = PrivateCommunityJoinRequiresInviteError(community_id)
        assert str(community_id) in str(error)
        assert error.community_id == community_id


class TestInsufficientCommunityRoleError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(InsufficientCommunityRoleError(uuid4(), uuid4(), "admin"), DomainError)

    def test_message_includes_required_role(self) -> None:
        community_id, user_id = uuid4(), uuid4()
        error = InsufficientCommunityRoleError(community_id, user_id, "admin")
        assert "admin" in str(error)
        assert error.required_role == "admin"
        assert error.community_id == community_id
        assert error.user_id == user_id


class TestCommunityOwnerRequiredError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommunityOwnerRequiredError(uuid4()), DomainError)

    def test_message_includes_community_id(self) -> None:
        community_id = uuid4()
        error = CommunityOwnerRequiredError(community_id)
        assert str(community_id) in str(error)
        assert error.community_id == community_id

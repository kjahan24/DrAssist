"""Tests for the Community module's domain exceptions."""

from uuid import uuid4

from app.modules.community.domain.exceptions import (
    CommunityCategoryNameRequiredError,
    CommunityCategoryNameTooLongError,
    CommunityCategoryNotFoundError,
    CommunityDescriptionRequiredError,
    CommunityDescriptionTooLongError,
    CommunityMediaEmptyError,
    CommunityMemberBlockedError,
    CommunityMembershipAlreadyExistsError,
    CommunityMembershipNotFoundError,
    CommunityNameRequiredError,
    CommunityNameTooLongError,
    CommunityNotFoundError,
    CommunityOwnerRequiredError,
    CommunityRuleNotFoundError,
    CommunityRuleTitleRequiredError,
    CommunityRuleTitleTooLongError,
    CommunityTagAlreadyAssignedError,
    CommunityTagNameRequiredError,
    CommunityTagNameTooLongError,
    CommunityTagNotAssignedError,
    CommunityTagNotFoundError,
    DuplicateCommunityCategoryNameError,
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


class TestCommunityCategoryNameRequiredError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommunityCategoryNameRequiredError(), DomainError)

    def test_message(self) -> None:
        assert "blank" in str(CommunityCategoryNameRequiredError())


class TestCommunityCategoryNameTooLongError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommunityCategoryNameTooLongError(100), DomainError)

    def test_message_includes_max_length(self) -> None:
        error = CommunityCategoryNameTooLongError(100)
        assert "100" in str(error)
        assert error.max_length == 100


class TestDuplicateCommunityCategoryNameError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(DuplicateCommunityCategoryNameError("Oncology"), DomainError)

    def test_message_includes_name(self) -> None:
        error = DuplicateCommunityCategoryNameError("Oncology")
        assert "Oncology" in str(error)
        assert error.name == "Oncology"


class TestCommunityCategoryNotFoundError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommunityCategoryNotFoundError(uuid4()), DomainError)

    def test_message_includes_category_id(self) -> None:
        category_id = uuid4()
        error = CommunityCategoryNotFoundError(category_id)
        assert str(category_id) in str(error)
        assert error.category_id == category_id


class TestCommunityTagNameRequiredError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommunityTagNameRequiredError(), DomainError)

    def test_message(self) -> None:
        assert "blank" in str(CommunityTagNameRequiredError())


class TestCommunityTagNameTooLongError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommunityTagNameTooLongError(50), DomainError)

    def test_message_includes_max_length(self) -> None:
        error = CommunityTagNameTooLongError(50)
        assert "50" in str(error)
        assert error.max_length == 50


class TestCommunityTagNotFoundError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommunityTagNotFoundError(uuid4()), DomainError)

    def test_message_includes_tag_id(self) -> None:
        tag_id = uuid4()
        error = CommunityTagNotFoundError(tag_id)
        assert str(tag_id) in str(error)
        assert error.tag_id == tag_id


class TestCommunityTagAlreadyAssignedError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommunityTagAlreadyAssignedError(uuid4(), uuid4()), DomainError)

    def test_message_includes_both_ids(self) -> None:
        community_id, tag_id = uuid4(), uuid4()
        error = CommunityTagAlreadyAssignedError(community_id, tag_id)
        assert str(community_id) in str(error)
        assert str(tag_id) in str(error)


class TestCommunityTagNotAssignedError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommunityTagNotAssignedError(uuid4(), uuid4()), DomainError)

    def test_message_includes_both_ids(self) -> None:
        community_id, tag_id = uuid4(), uuid4()
        error = CommunityTagNotAssignedError(community_id, tag_id)
        assert str(community_id) in str(error)
        assert str(tag_id) in str(error)


class TestCommunityRuleTitleRequiredError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommunityRuleTitleRequiredError(), DomainError)

    def test_message(self) -> None:
        assert "blank" in str(CommunityRuleTitleRequiredError())


class TestCommunityRuleTitleTooLongError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommunityRuleTitleTooLongError(200), DomainError)

    def test_message_includes_max_length(self) -> None:
        error = CommunityRuleTitleTooLongError(200)
        assert "200" in str(error)
        assert error.max_length == 200


class TestCommunityRuleNotFoundError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommunityRuleNotFoundError(uuid4()), DomainError)

    def test_message_includes_rule_id(self) -> None:
        rule_id = uuid4()
        error = CommunityRuleNotFoundError(rule_id)
        assert str(rule_id) in str(error)
        assert error.rule_id == rule_id


class TestCommunityMediaEmptyError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommunityMediaEmptyError("avatar"), DomainError)

    def test_message_includes_field(self) -> None:
        error = CommunityMediaEmptyError("banner")
        assert "banner" in str(error)
        assert error.field == "banner"

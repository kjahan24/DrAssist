"""Direct unit tests for `_authorization.py` — the role-hierarchy and
visibility-tier helpers shared by every mutating/reading Community
Answers service. Exercises every branch (PUBLIC/MEMBERS_ONLY/PRIVATE
tiers, each role rank) directly, since not every branch is reachable
through every individual service's own test file."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityMemberStatus, CommunityRole
from app.modules.community_answers.application.services._authorization import (
    ensure_can_author_action,
    ensure_can_create,
    ensure_can_select_best_answer,
    ensure_can_view,
    ensure_can_view_question,
    ensure_is_moderator,
)
from app.modules.community_answers.domain.entities import CommunityAnswer
from app.modules.community_answers.domain.enums import AnswerVisibility
from app.modules.community_answers.domain.exceptions import (
    AnswerMembershipRequiredError,
    AnswerNotViewableError,
    InsufficientAnswerRoleError,
    InsufficientBestAnswerRoleError,
    QuestionNotViewableForAnswerError,
)
from app.modules.community_answers.domain.value_objects import AnswerBody
from app.modules.community_questions.public.dto import QuestionVisibility
from tests.unit.modules.community_answers.application.fakes import (
    make_member_summary,
    make_question_summary,
)


def _answer(**overrides: object) -> CommunityAnswer:
    defaults: dict[str, object] = {
        "question_id": uuid4(),
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "topic_id": uuid4(),
        "author_id": uuid4(),
        "body": AnswerBody("Body."),
    }
    defaults.update(overrides)
    return CommunityAnswer.create(**defaults)  # type: ignore[arg-type]


class TestEnsureCanCreate:
    def test_active_member_is_allowed(self) -> None:
        community_id, user_id = uuid4(), uuid4()
        member = make_member_summary(community_id=community_id, user_id=user_id)
        ensure_can_create(member, community_id=community_id, user_id=user_id)

    def test_no_membership_raises(self) -> None:
        with pytest.raises(AnswerMembershipRequiredError):
            ensure_can_create(None, community_id=uuid4(), user_id=uuid4())

    def test_inactive_membership_raises(self) -> None:
        community_id, user_id = uuid4(), uuid4()
        member = make_member_summary(
            community_id=community_id, user_id=user_id, status=CommunityMemberStatus.BLOCKED
        )
        with pytest.raises(AnswerMembershipRequiredError):
            ensure_can_create(member, community_id=community_id, user_id=user_id)


class TestEnsureCanAuthorAction:
    def test_the_author_is_always_allowed(self) -> None:
        author_id, community_id = uuid4(), uuid4()
        ensure_can_author_action(
            None, community_id=community_id, user_id=author_id, author_id=author_id
        )

    def test_moderator_is_allowed_for_someone_elses_answer(self) -> None:
        community_id, moderator_id, author_id = uuid4(), uuid4(), uuid4()
        member = make_member_summary(
            community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
        )
        ensure_can_author_action(
            member, community_id=community_id, user_id=moderator_id, author_id=author_id
        )

    def test_admin_is_allowed(self) -> None:
        community_id, admin_id, author_id = uuid4(), uuid4(), uuid4()
        member = make_member_summary(
            community_id=community_id, user_id=admin_id, role=CommunityRole.ADMIN
        )
        ensure_can_author_action(
            member, community_id=community_id, user_id=admin_id, author_id=author_id
        )

    def test_owner_is_allowed(self) -> None:
        community_id, owner_id, author_id = uuid4(), uuid4(), uuid4()
        member = make_member_summary(
            community_id=community_id, user_id=owner_id, role=CommunityRole.OWNER
        )
        ensure_can_author_action(
            member, community_id=community_id, user_id=owner_id, author_id=author_id
        )

    def test_plain_member_raises_for_someone_elses_answer(self) -> None:
        community_id, member_id, author_id = uuid4(), uuid4(), uuid4()
        member = make_member_summary(community_id=community_id, user_id=member_id)
        with pytest.raises(InsufficientAnswerRoleError):
            ensure_can_author_action(
                member, community_id=community_id, user_id=member_id, author_id=author_id
            )

    def test_no_membership_raises_for_someone_elses_answer(self) -> None:
        with pytest.raises(AnswerMembershipRequiredError):
            ensure_can_author_action(None, community_id=uuid4(), user_id=uuid4(), author_id=uuid4())


class TestEnsureIsModerator:
    def test_moderator_is_allowed(self) -> None:
        community_id, moderator_id = uuid4(), uuid4()
        member = make_member_summary(
            community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
        )
        ensure_is_moderator(member, community_id=community_id, user_id=moderator_id)

    def test_plain_member_raises(self) -> None:
        community_id, member_id = uuid4(), uuid4()
        member = make_member_summary(community_id=community_id, user_id=member_id)
        with pytest.raises(InsufficientAnswerRoleError):
            ensure_is_moderator(member, community_id=community_id, user_id=member_id)

    def test_no_membership_raises(self) -> None:
        with pytest.raises(AnswerMembershipRequiredError):
            ensure_is_moderator(None, community_id=uuid4(), user_id=uuid4())


class TestEnsureCanView:
    def test_public_answer_is_viewable_with_no_member_and_no_user(self) -> None:
        answer = _answer(visibility=AnswerVisibility.PUBLIC)
        ensure_can_view(answer, None, user_id=None)

    def test_members_only_answer_raises_for_no_member(self) -> None:
        answer = _answer(visibility=AnswerVisibility.MEMBERS_ONLY)
        with pytest.raises(AnswerNotViewableError):
            ensure_can_view(answer, None, user_id=uuid4())

    def test_members_only_answer_raises_for_inactive_member(self) -> None:
        answer = _answer(visibility=AnswerVisibility.MEMBERS_ONLY)
        member = make_member_summary(
            community_id=answer.community_id, status=CommunityMemberStatus.BLOCKED
        )
        with pytest.raises(AnswerNotViewableError):
            ensure_can_view(answer, member, user_id=uuid4())

    def test_members_only_answer_allowed_for_active_member(self) -> None:
        answer = _answer(visibility=AnswerVisibility.MEMBERS_ONLY)
        member = make_member_summary(
            community_id=answer.community_id, status=CommunityMemberStatus.ACTIVE
        )
        ensure_can_view(answer, member, user_id=uuid4())

    def test_private_answer_allowed_for_its_own_author(self) -> None:
        answer = _answer(visibility=AnswerVisibility.PRIVATE)
        ensure_can_view(answer, None, user_id=answer.author_id)

    def test_private_answer_raises_for_a_plain_member(self) -> None:
        answer = _answer(visibility=AnswerVisibility.PRIVATE)
        member = make_member_summary(community_id=answer.community_id, role=CommunityRole.MEMBER)
        with pytest.raises(AnswerNotViewableError):
            ensure_can_view(answer, member, user_id=uuid4())

    def test_private_answer_allowed_for_a_moderator(self) -> None:
        answer = _answer(visibility=AnswerVisibility.PRIVATE)
        member = make_member_summary(community_id=answer.community_id, role=CommunityRole.MODERATOR)
        ensure_can_view(answer, member, user_id=uuid4())

    def test_private_answer_raises_for_no_user_and_no_member(self) -> None:
        answer = _answer(visibility=AnswerVisibility.PRIVATE)
        with pytest.raises(AnswerNotViewableError):
            ensure_can_view(answer, None, user_id=None)


class TestEnsureCanViewQuestion:
    def test_public_question_is_viewable_with_no_member_and_no_user(self) -> None:
        question = make_question_summary(visibility=QuestionVisibility.PUBLIC)
        ensure_can_view_question(question, None, user_id=None)

    def test_members_only_question_raises_for_no_member(self) -> None:
        question = make_question_summary(visibility=QuestionVisibility.MEMBERS_ONLY)
        with pytest.raises(QuestionNotViewableForAnswerError):
            ensure_can_view_question(question, None, user_id=uuid4())

    def test_members_only_question_allowed_for_active_member(self) -> None:
        question = make_question_summary(visibility=QuestionVisibility.MEMBERS_ONLY)
        member = make_member_summary(
            community_id=question.community_id, status=CommunityMemberStatus.ACTIVE
        )
        ensure_can_view_question(question, member, user_id=uuid4())

    def test_private_question_allowed_for_its_own_author(self) -> None:
        author_id = uuid4()
        question = make_question_summary(visibility=QuestionVisibility.PRIVATE, author_id=author_id)
        ensure_can_view_question(question, None, user_id=author_id)

    def test_private_question_raises_for_a_plain_member(self) -> None:
        question = make_question_summary(visibility=QuestionVisibility.PRIVATE, author_id=uuid4())
        member = make_member_summary(community_id=question.community_id, role=CommunityRole.MEMBER)
        with pytest.raises(QuestionNotViewableForAnswerError):
            ensure_can_view_question(question, member, user_id=uuid4())

    def test_private_question_allowed_for_a_moderator(self) -> None:
        question = make_question_summary(visibility=QuestionVisibility.PRIVATE, author_id=uuid4())
        member = make_member_summary(
            community_id=question.community_id, role=CommunityRole.MODERATOR
        )
        ensure_can_view_question(question, member, user_id=uuid4())


class TestEnsureCanSelectBestAnswer:
    def test_the_question_author_is_always_allowed(self) -> None:
        question_id, question_author_id = uuid4(), uuid4()
        ensure_can_select_best_answer(
            None,
            community_id=uuid4(),
            user_id=question_author_id,
            question_id=question_id,
            question_author_id=question_author_id,
        )

    def test_moderator_is_allowed(self) -> None:
        community_id, moderator_id, question_id = uuid4(), uuid4(), uuid4()
        member = make_member_summary(
            community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
        )
        ensure_can_select_best_answer(
            member,
            community_id=community_id,
            user_id=moderator_id,
            question_id=question_id,
            question_author_id=uuid4(),
        )

    def test_plain_member_raises(self) -> None:
        community_id, member_id, question_id = uuid4(), uuid4(), uuid4()
        member = make_member_summary(community_id=community_id, user_id=member_id)
        with pytest.raises(InsufficientBestAnswerRoleError):
            ensure_can_select_best_answer(
                member,
                community_id=community_id,
                user_id=member_id,
                question_id=question_id,
                question_author_id=uuid4(),
            )

    def test_the_answers_own_author_without_membership_raises(self) -> None:
        with pytest.raises(AnswerMembershipRequiredError):
            ensure_can_select_best_answer(
                None,
                community_id=uuid4(),
                user_id=uuid4(),
                question_id=uuid4(),
                question_author_id=uuid4(),
            )

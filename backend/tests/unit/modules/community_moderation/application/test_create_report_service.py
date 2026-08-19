"""Unit tests for `CreateReportService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community_moderation.application.dto import CreateReportInput
from app.modules.community_moderation.application.services.create_report_service import (
    CreateReportService,
)
from app.modules.community_moderation.domain.enums import (
    ModerationTargetType,
    ReportPriority,
    ReportReason,
)
from app.modules.community_moderation.domain.events import ReportCreated
from app.modules.community_moderation.domain.exceptions import (
    DuplicateOpenReportError,
    ModerationMembershipRequiredError,
    ReportTargetNotFoundError,
)
from tests.unit.modules.community_moderation.application.fakes import (
    FakeAnswerQueryPort,
    FakeCommentQueryPort,
    FakeCommunityQueryPort,
    FakeCommunityReportRepository,
    FakePostQueryPort,
    FakeQuestionQueryPort,
    FakeUnitOfWork,
    FakeUserQueryPort,
    make_answer_summary,
    make_comment_summary,
    make_community_summary,
    make_member_summary,
    make_post_summary,
    make_question_summary,
    make_user_summary,
)


def _seeded() -> (
    tuple[
        CreateReportService,
        FakeCommunityReportRepository,
        FakePostQueryPort,
        FakeCommunityQueryPort,
        FakeUserQueryPort,
        FakeUnitOfWork,
    ]
):
    reports = FakeCommunityReportRepository()
    posts = FakePostQueryPort()
    questions = FakeQuestionQueryPort()
    answers = FakeAnswerQueryPort()
    comments = FakeCommentQueryPort()
    communities = FakeCommunityQueryPort()
    users = FakeUserQueryPort()
    uow = FakeUnitOfWork()
    service = CreateReportService(
        report_repository=reports,
        post_query_port=posts,
        question_query_port=questions,
        answer_query_port=answers,
        comment_query_port=comments,
        community_query_port=communities,
        user_query_port=users,
        unit_of_work=uow,
    )
    return service, reports, posts, communities, users, uow


class TestCreateReportOnContentTarget:
    async def test_creates_a_report_against_a_post(self) -> None:
        service, reports, posts, communities, _, _ = _seeded()
        org_id, community_id, post_id, reporter_id = uuid4(), uuid4(), uuid4(), uuid4()
        posts.add_post(
            make_post_summary(post_id=post_id, community_id=community_id, organization_id=org_id)
        )
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=reporter_id)
        )

        output = await service.execute(
            CreateReportInput(
                organization_id=org_id,
                community_id=community_id,
                reporter_id=reporter_id,
                target_type=ModerationTargetType.POST,
                target_id=post_id,
                reason=ReportReason.SPAM,
            )
        )
        assert output.target_id == post_id
        stored = await reports.get_by_id(output.report_id)
        assert stored is not None

    async def test_unknown_target_raises(self) -> None:
        service, _, _, communities, _, _ = _seeded()
        org_id, community_id, reporter_id = uuid4(), uuid4(), uuid4()
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=reporter_id)
        )
        with pytest.raises(ReportTargetNotFoundError):
            await service.execute(
                CreateReportInput(
                    organization_id=org_id,
                    community_id=community_id,
                    reporter_id=reporter_id,
                    target_type=ModerationTargetType.POST,
                    target_id=uuid4(),
                    reason=ReportReason.SPAM,
                )
            )

    async def test_cross_tenant_target_raises_not_found(self) -> None:
        service, _, posts, communities, _, _ = _seeded()
        community_id, post_id, reporter_id = uuid4(), uuid4(), uuid4()
        posts.add_post(
            make_post_summary(post_id=post_id, community_id=community_id, organization_id=uuid4())
        )
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=reporter_id)
        )
        with pytest.raises(ReportTargetNotFoundError):
            await service.execute(
                CreateReportInput(
                    organization_id=uuid4(),
                    community_id=community_id,
                    reporter_id=reporter_id,
                    target_type=ModerationTargetType.POST,
                    target_id=post_id,
                    reason=ReportReason.SPAM,
                )
            )

    async def test_mismatched_community_id_raises_not_found(self) -> None:
        service, _, posts, communities, _, _ = _seeded()
        org_id, real_community_id, wrong_community_id = uuid4(), uuid4(), uuid4()
        post_id, reporter_id = uuid4(), uuid4()
        posts.add_post(
            make_post_summary(
                post_id=post_id, community_id=real_community_id, organization_id=org_id
            )
        )
        communities.add_membership(
            make_member_summary(community_id=wrong_community_id, user_id=reporter_id)
        )
        with pytest.raises(ReportTargetNotFoundError):
            await service.execute(
                CreateReportInput(
                    organization_id=org_id,
                    community_id=wrong_community_id,
                    reporter_id=reporter_id,
                    target_type=ModerationTargetType.POST,
                    target_id=post_id,
                    reason=ReportReason.SPAM,
                )
            )

    async def test_reporter_must_be_an_active_member(self) -> None:
        service, _, posts, _, _, _ = _seeded()
        org_id, community_id, post_id = uuid4(), uuid4(), uuid4()
        posts.add_post(
            make_post_summary(post_id=post_id, community_id=community_id, organization_id=org_id)
        )
        with pytest.raises(ModerationMembershipRequiredError):
            await service.execute(
                CreateReportInput(
                    organization_id=org_id,
                    community_id=community_id,
                    reporter_id=uuid4(),
                    target_type=ModerationTargetType.POST,
                    target_id=post_id,
                    reason=ReportReason.SPAM,
                )
            )

    async def test_second_open_report_by_the_same_reporter_raises(self) -> None:
        service, _, posts, communities, _, _ = _seeded()
        org_id, community_id, post_id, reporter_id = uuid4(), uuid4(), uuid4(), uuid4()
        posts.add_post(
            make_post_summary(post_id=post_id, community_id=community_id, organization_id=org_id)
        )
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=reporter_id)
        )
        await service.execute(
            CreateReportInput(
                organization_id=org_id,
                community_id=community_id,
                reporter_id=reporter_id,
                target_type=ModerationTargetType.POST,
                target_id=post_id,
                reason=ReportReason.SPAM,
            )
        )
        with pytest.raises(DuplicateOpenReportError):
            await service.execute(
                CreateReportInput(
                    organization_id=org_id,
                    community_id=community_id,
                    reporter_id=reporter_id,
                    target_type=ModerationTargetType.POST,
                    target_id=post_id,
                    reason=ReportReason.HARASSMENT,
                )
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, posts, communities, _, uow = _seeded()
        org_id, community_id, post_id, reporter_id = uuid4(), uuid4(), uuid4(), uuid4()
        posts.add_post(
            make_post_summary(post_id=post_id, community_id=community_id, organization_id=org_id)
        )
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=reporter_id)
        )
        await service.execute(
            CreateReportInput(
                organization_id=org_id,
                community_id=community_id,
                reporter_id=reporter_id,
                target_type=ModerationTargetType.POST,
                target_id=post_id,
                reason=ReportReason.SPAM,
            )
        )
        assert uow.committed is True

    async def test_publishes_a_report_created_event(self) -> None:
        service, _, posts, communities, _, uow = _seeded()
        org_id, community_id, post_id, reporter_id = uuid4(), uuid4(), uuid4(), uuid4()
        posts.add_post(
            make_post_summary(post_id=post_id, community_id=community_id, organization_id=org_id)
        )
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=reporter_id)
        )
        await service.execute(
            CreateReportInput(
                organization_id=org_id,
                community_id=community_id,
                reporter_id=reporter_id,
                target_type=ModerationTargetType.POST,
                target_id=post_id,
                reason=ReportReason.SPAM,
            )
        )
        assert any(isinstance(e, ReportCreated) for e in uow.published_events)

    async def test_priority_is_derived_from_reason(self) -> None:
        service, _, posts, communities, _, _ = _seeded()
        org_id, community_id, post_id, reporter_id = uuid4(), uuid4(), uuid4(), uuid4()
        posts.add_post(
            make_post_summary(post_id=post_id, community_id=community_id, organization_id=org_id)
        )
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=reporter_id)
        )
        output = await service.execute(
            CreateReportInput(
                organization_id=org_id,
                community_id=community_id,
                reporter_id=reporter_id,
                target_type=ModerationTargetType.POST,
                target_id=post_id,
                reason=ReportReason.DANGEROUS_MEDICAL_ADVICE,
            )
        )
        assert output.priority.value == "high"


class TestCreateReportOnUserTarget:
    async def test_creates_a_report_against_a_user(self) -> None:
        service, reports, _, communities, users, _ = _seeded()
        org_id, community_id, reported_user_id, reporter_id = (
            uuid4(),
            uuid4(),
            uuid4(),
            uuid4(),
        )
        communities.add_community(
            make_community_summary(community_id=community_id, organization_id=org_id)
        )
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=reporter_id)
        )
        users.add_user(make_user_summary(user_id=reported_user_id, organization_id=org_id))

        output = await service.execute(
            CreateReportInput(
                organization_id=org_id,
                community_id=community_id,
                reporter_id=reporter_id,
                target_type=ModerationTargetType.USER,
                target_id=reported_user_id,
                reason=ReportReason.HARASSMENT,
            )
        )
        assert output.target_id == reported_user_id
        assert output.target_type is ModerationTargetType.USER

    async def test_unknown_user_target_raises(self) -> None:
        service, _, _, communities, _, _ = _seeded()
        org_id, community_id, reporter_id = uuid4(), uuid4(), uuid4()
        communities.add_community(
            make_community_summary(community_id=community_id, organization_id=org_id)
        )
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=reporter_id)
        )
        with pytest.raises(ReportTargetNotFoundError):
            await service.execute(
                CreateReportInput(
                    organization_id=org_id,
                    community_id=community_id,
                    reporter_id=reporter_id,
                    target_type=ModerationTargetType.USER,
                    target_id=uuid4(),
                    reason=ReportReason.HARASSMENT,
                )
            )

    async def test_unknown_community_context_raises(self) -> None:
        service, _, _, _, users, _ = _seeded()
        org_id, reported_user_id, reporter_id = uuid4(), uuid4(), uuid4()
        users.add_user(make_user_summary(user_id=reported_user_id, organization_id=org_id))
        with pytest.raises(ReportTargetNotFoundError):
            await service.execute(
                CreateReportInput(
                    organization_id=org_id,
                    community_id=uuid4(),
                    reporter_id=reporter_id,
                    target_type=ModerationTargetType.USER,
                    target_id=reported_user_id,
                    reason=ReportReason.HARASSMENT,
                )
            )


def _seeded_with_targets() -> (
    tuple[
        CreateReportService,
        FakeQuestionQueryPort,
        FakeAnswerQueryPort,
        FakeCommentQueryPort,
        FakeCommunityQueryPort,
    ]
):
    reports = FakeCommunityReportRepository()
    posts = FakePostQueryPort()
    questions = FakeQuestionQueryPort()
    answers = FakeAnswerQueryPort()
    comments = FakeCommentQueryPort()
    communities = FakeCommunityQueryPort()
    users = FakeUserQueryPort()
    uow = FakeUnitOfWork()
    service = CreateReportService(
        report_repository=reports,
        post_query_port=posts,
        question_query_port=questions,
        answer_query_port=answers,
        comment_query_port=comments,
        community_query_port=communities,
        user_query_port=users,
        unit_of_work=uow,
    )
    return service, questions, answers, comments, communities


class TestCreateReportOnEveryPolymorphicTargetType:
    """`ModerationTargetType` names six members; `TestCreateReportOnContentTarget`
    already exercises `POST` and `TestCreateReportOnUserTarget` exercises
    `USER` — this class covers the remaining four (`QUESTION`/`ANSWER`/
    `COMMENT`/`COMMUNITY`), confirming `_target_resolution.py`'s "one
    resolver for all six target types" actually dispatches correctly for
    every one of them, not just the two already covered above."""

    async def test_creates_a_report_against_a_question(self) -> None:
        service, questions, _, _, communities = _seeded_with_targets()
        org_id, community_id, question_id, reporter_id = uuid4(), uuid4(), uuid4(), uuid4()
        questions.add_question(
            make_question_summary(
                question_id=question_id, community_id=community_id, organization_id=org_id
            )
        )
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=reporter_id)
        )
        output = await service.execute(
            CreateReportInput(
                organization_id=org_id,
                community_id=community_id,
                reporter_id=reporter_id,
                target_type=ModerationTargetType.QUESTION,
                target_id=question_id,
                reason=ReportReason.MEDICAL_MISINFORMATION,
            )
        )
        assert output.target_type is ModerationTargetType.QUESTION
        assert output.target_id == question_id

    async def test_creates_a_report_against_an_answer(self) -> None:
        service, _, answers, _, communities = _seeded_with_targets()
        org_id, community_id, answer_id, reporter_id = uuid4(), uuid4(), uuid4(), uuid4()
        answers.add_answer(
            make_answer_summary(
                answer_id=answer_id, community_id=community_id, organization_id=org_id
            )
        )
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=reporter_id)
        )
        output = await service.execute(
            CreateReportInput(
                organization_id=org_id,
                community_id=community_id,
                reporter_id=reporter_id,
                target_type=ModerationTargetType.ANSWER,
                target_id=answer_id,
                reason=ReportReason.DANGEROUS_MEDICAL_ADVICE,
            )
        )
        assert output.target_type is ModerationTargetType.ANSWER
        assert output.target_id == answer_id

    async def test_creates_a_report_against_a_comment(self) -> None:
        service, _, _, comments, communities = _seeded_with_targets()
        org_id, community_id, comment_id, reporter_id = uuid4(), uuid4(), uuid4(), uuid4()
        comments.add_comment(
            make_comment_summary(
                comment_id=comment_id, community_id=community_id, organization_id=org_id
            )
        )
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=reporter_id)
        )
        output = await service.execute(
            CreateReportInput(
                organization_id=org_id,
                community_id=community_id,
                reporter_id=reporter_id,
                target_type=ModerationTargetType.COMMENT,
                target_id=comment_id,
                reason=ReportReason.ABUSE,
            )
        )
        assert output.target_type is ModerationTargetType.COMMENT
        assert output.target_id == comment_id

    async def test_creates_a_report_against_a_community(self) -> None:
        service, _, _, _, communities = _seeded_with_targets()
        org_id, community_id, reporter_id = uuid4(), uuid4(), uuid4()
        communities.add_community(
            make_community_summary(community_id=community_id, organization_id=org_id)
        )
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=reporter_id)
        )
        output = await service.execute(
            CreateReportInput(
                organization_id=org_id,
                community_id=community_id,
                reporter_id=reporter_id,
                target_type=ModerationTargetType.COMMUNITY,
                target_id=community_id,
                reason=ReportReason.ILLEGAL_CONTENT,
            )
        )
        assert output.target_type is ModerationTargetType.COMMUNITY
        assert output.target_id == community_id
        assert output.priority is ReportPriority.HIGH

    async def test_community_target_with_mismatched_id_raises(self) -> None:
        """For a `COMMUNITY` target, `target_id` and `community_id` must
        match — the target *is* the community."""
        service, _, _, _, communities = _seeded_with_targets()
        org_id, real_community_id, wrong_community_id, reporter_id = (
            uuid4(),
            uuid4(),
            uuid4(),
            uuid4(),
        )
        communities.add_community(
            make_community_summary(community_id=real_community_id, organization_id=org_id)
        )
        communities.add_membership(
            make_member_summary(community_id=wrong_community_id, user_id=reporter_id)
        )
        with pytest.raises(ReportTargetNotFoundError):
            await service.execute(
                CreateReportInput(
                    organization_id=org_id,
                    community_id=wrong_community_id,
                    reporter_id=reporter_id,
                    target_type=ModerationTargetType.COMMUNITY,
                    target_id=real_community_id,
                    reason=ReportReason.ILLEGAL_CONTENT,
                )
            )

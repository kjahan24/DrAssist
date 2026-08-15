"""Tests for the Community Questions module's domain enums."""

from enum import StrEnum

from app.modules.community_questions.domain.enums import (
    QuestionStatus,
    QuestionType,
    QuestionVisibility,
)


class TestQuestionType:
    def test_is_a_str_enum(self) -> None:
        assert issubclass(QuestionType, StrEnum)

    def test_has_exactly_eight_members(self) -> None:
        assert len(QuestionType) == 8

    def test_general_value(self) -> None:
        assert QuestionType.GENERAL.value == "general"

    def test_clinical_value(self) -> None:
        assert QuestionType.CLINICAL.value == "clinical"

    def test_patient_experience_value(self) -> None:
        assert QuestionType.PATIENT_EXPERIENCE.value == "patient_experience"

    def test_treatment_advice_value(self) -> None:
        assert QuestionType.TREATMENT_ADVICE.value == "treatment_advice"

    def test_medication_question_value(self) -> None:
        assert QuestionType.MEDICATION_QUESTION.value == "medication_question"

    def test_diagnosis_discussion_value(self) -> None:
        assert QuestionType.DIAGNOSIS_DISCUSSION.value == "diagnosis_discussion"

    def test_research_question_value(self) -> None:
        assert QuestionType.RESEARCH_QUESTION.value == "research_question"

    def test_educational_question_value(self) -> None:
        assert QuestionType.EDUCATIONAL_QUESTION.value == "educational_question"

    def test_members_are_strings(self) -> None:
        for member in QuestionType:
            assert isinstance(member, str)


class TestQuestionStatus:
    def test_is_a_str_enum(self) -> None:
        assert issubclass(QuestionStatus, StrEnum)

    def test_has_exactly_five_members(self) -> None:
        assert len(QuestionStatus) == 5

    def test_draft_value(self) -> None:
        assert QuestionStatus.DRAFT.value == "draft"

    def test_published_value(self) -> None:
        assert QuestionStatus.PUBLISHED.value == "published"

    def test_closed_value(self) -> None:
        assert QuestionStatus.CLOSED.value == "closed"

    def test_archived_value(self) -> None:
        assert QuestionStatus.ARCHIVED.value == "archived"

    def test_deleted_value(self) -> None:
        assert QuestionStatus.DELETED.value == "deleted"

    def test_members_are_strings(self) -> None:
        for member in QuestionStatus:
            assert isinstance(member, str)


class TestQuestionVisibility:
    def test_is_a_str_enum(self) -> None:
        assert issubclass(QuestionVisibility, StrEnum)

    def test_has_exactly_three_members(self) -> None:
        assert len(QuestionVisibility) == 3

    def test_public_value(self) -> None:
        assert QuestionVisibility.PUBLIC.value == "public"

    def test_members_only_value(self) -> None:
        assert QuestionVisibility.MEMBERS_ONLY.value == "members_only"

    def test_private_value(self) -> None:
        assert QuestionVisibility.PRIVATE.value == "private"

    def test_members_are_strings(self) -> None:
        for member in QuestionVisibility:
            assert isinstance(member, str)

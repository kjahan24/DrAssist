"""Tests for the Community Posts module's domain enums."""

from enum import StrEnum

from app.modules.community_posts.domain.enums import PostStatus, PostType, PostVisibility


class TestPostType:
    def test_is_a_str_enum(self) -> None:
        assert issubclass(PostType, StrEnum)

    def test_has_exactly_eight_members(self) -> None:
        assert len(PostType) == 8

    def test_discussion_value(self) -> None:
        assert PostType.DISCUSSION.value == "discussion"

    def test_experience_value(self) -> None:
        assert PostType.EXPERIENCE.value == "experience"

    def test_clinical_case_value(self) -> None:
        assert PostType.CLINICAL_CASE.value == "clinical_case"

    def test_medical_news_value(self) -> None:
        assert PostType.MEDICAL_NEWS.value == "medical_news"

    def test_research_value(self) -> None:
        assert PostType.RESEARCH.value == "research"

    def test_educational_value(self) -> None:
        assert PostType.EDUCATIONAL.value == "educational"

    def test_clinical_pearl_value(self) -> None:
        assert PostType.CLINICAL_PEARL.value == "clinical_pearl"

    def test_announcement_value(self) -> None:
        assert PostType.ANNOUNCEMENT.value == "announcement"

    def test_members_are_strings(self) -> None:
        for member in PostType:
            assert isinstance(member, str)


class TestPostStatus:
    def test_is_a_str_enum(self) -> None:
        assert issubclass(PostStatus, StrEnum)

    def test_has_exactly_three_members(self) -> None:
        assert len(PostStatus) == 3

    def test_draft_value(self) -> None:
        assert PostStatus.DRAFT.value == "draft"

    def test_published_value(self) -> None:
        assert PostStatus.PUBLISHED.value == "published"

    def test_archived_value(self) -> None:
        assert PostStatus.ARCHIVED.value == "archived"

    def test_members_are_strings(self) -> None:
        for member in PostStatus:
            assert isinstance(member, str)


class TestPostVisibility:
    def test_is_a_str_enum(self) -> None:
        assert issubclass(PostVisibility, StrEnum)

    def test_has_exactly_three_members(self) -> None:
        assert len(PostVisibility) == 3

    def test_public_value(self) -> None:
        assert PostVisibility.PUBLIC.value == "public"

    def test_members_only_value(self) -> None:
        assert PostVisibility.MEMBERS_ONLY.value == "members_only"

    def test_private_value(self) -> None:
        assert PostVisibility.PRIVATE.value == "private"

    def test_members_are_strings(self) -> None:
        for member in PostVisibility:
            assert isinstance(member, str)

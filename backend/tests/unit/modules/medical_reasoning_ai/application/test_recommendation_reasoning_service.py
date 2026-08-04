"""Unit tests for `RecommendationReasoningService`."""

from app.modules.medical_reasoning_ai.application.services.recommendation_reasoning_service import (
    RecommendationReasoningService,
)


class TestFindDuplicate:
    def test_returns_the_repeated_item(self) -> None:
        service = RecommendationReasoningService()

        duplicate = service.find_duplicate(("CBC", "BMP", "CBC"))

        assert duplicate == "CBC"

    def test_is_case_and_whitespace_insensitive(self) -> None:
        service = RecommendationReasoningService()

        duplicate = service.find_duplicate(("CBC", "  cbc  "))

        assert duplicate == "  cbc  "

    def test_returns_none_when_no_duplicates(self) -> None:
        service = RecommendationReasoningService()

        assert service.find_duplicate(("CBC", "BMP")) is None

    def test_returns_none_for_an_empty_list(self) -> None:
        service = RecommendationReasoningService()

        assert service.find_duplicate(()) is None

    def test_ignores_blank_entries(self) -> None:
        service = RecommendationReasoningService()

        assert service.find_duplicate(("", "  ", "")) is None


class TestDeduplicate:
    def test_removes_repeated_entries_preserving_first_occurrence_order(self) -> None:
        service = RecommendationReasoningService()

        result = service.deduplicate(("CBC", "BMP", "cbc", "CBC"))

        assert result == ("CBC", "BMP")

    def test_drops_blank_entries(self) -> None:
        service = RecommendationReasoningService()

        result = service.deduplicate(("CBC", "", "  "))

        assert result == ("CBC",)

    def test_empty_input_returns_empty(self) -> None:
        service = RecommendationReasoningService()

        assert service.deduplicate(()) == ()

    def test_no_duplicates_returns_the_same_items(self) -> None:
        service = RecommendationReasoningService()

        result = service.deduplicate(("CBC", "BMP"))

        assert result == ("CBC", "BMP")

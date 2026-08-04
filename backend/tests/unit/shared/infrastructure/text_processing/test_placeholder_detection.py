"""Unit tests for `find_placeholder_marker`."""

import pytest

from app.shared.infrastructure.text_processing.placeholder_detection import (
    find_placeholder_marker,
)


class TestFindPlaceholderMarker:
    @pytest.mark.parametrize(
        "text",
        [
            "Patient reports [insert history here].",
            "Findings: [PLACEHOLDER]",
            "Exam notes <insert findings>",
            "Follow up: TBD",
            "TODO: complete this section",
            "Reference code XXX",
            "Lorem ipsum dolor sit amet",
            "Contact [Patient Name] for follow-up",
        ],
    )
    def test_detects_known_placeholder_markers(self, text: str) -> None:
        assert find_placeholder_marker(text) is not None

    def test_returns_none_for_ordinary_clinical_text(self) -> None:
        assert find_placeholder_marker("Patient reports headache for three days.") is None

    def test_returns_none_for_empty_text(self) -> None:
        assert find_placeholder_marker("") is None

    def test_returned_value_is_the_matched_substring(self) -> None:
        result = find_placeholder_marker("Assessment: TBD pending labs")
        assert result is not None
        assert result.lower() == "tbd"

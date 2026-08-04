"""Unit tests for the AI Clinical Copilot module's domain enums."""

from app.modules.ai_copilot.domain.enums import CopilotOutputFormat


class TestCopilotOutputFormat:
    def test_has_exactly_three_members(self) -> None:
        assert {member.value for member in CopilotOutputFormat} == {"json", "markdown", "text"}

    def test_json_value(self) -> None:
        assert CopilotOutputFormat.JSON.value == "json"

    def test_markdown_value(self) -> None:
        assert CopilotOutputFormat.MARKDOWN.value == "markdown"

    def test_text_value(self) -> None:
        assert CopilotOutputFormat.TEXT.value == "text"

    def test_is_constructible_from_its_string_value(self) -> None:
        assert CopilotOutputFormat("json") is CopilotOutputFormat.JSON

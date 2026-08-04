"""Unit tests for `DefaultAIResponseValidator`."""

import pytest

from app.modules.ai_copilot.domain.enums import CopilotOutputFormat
from app.modules.ai_copilot.domain.exceptions import AIResponseValidationError
from app.modules.ai_copilot.infrastructure.validation.response_validator import (
    DefaultAIResponseValidator,
)


class TestValidateJSON:
    def test_accepts_a_populated_dict(self) -> None:
        validator = DefaultAIResponseValidator()
        validator.validate({"a": 1}, output_format=CopilotOutputFormat.JSON, raw_text="{}")

    def test_accepts_a_populated_list(self) -> None:
        validator = DefaultAIResponseValidator()
        validator.validate([1, 2], output_format=CopilotOutputFormat.JSON, raw_text="[]")

    def test_rejects_none(self) -> None:
        validator = DefaultAIResponseValidator()
        with pytest.raises(AIResponseValidationError):
            validator.validate(None, output_format=CopilotOutputFormat.JSON, raw_text="null")

    def test_rejects_empty_dict(self) -> None:
        validator = DefaultAIResponseValidator()
        with pytest.raises(AIResponseValidationError):
            validator.validate({}, output_format=CopilotOutputFormat.JSON, raw_text="{}")

    def test_rejects_empty_list(self) -> None:
        validator = DefaultAIResponseValidator()
        with pytest.raises(AIResponseValidationError):
            validator.validate([], output_format=CopilotOutputFormat.JSON, raw_text="[]")

    def test_accepts_a_scalar(self) -> None:
        validator = DefaultAIResponseValidator()
        validator.validate("a string", output_format=CopilotOutputFormat.JSON, raw_text='"x"')


class TestValidateMarkdown:
    def test_accepts_sections_with_content(self) -> None:
        validator = DefaultAIResponseValidator()
        validator.validate(
            {"Heading": "body"}, output_format=CopilotOutputFormat.MARKDOWN, raw_text=""
        )

    def test_rejects_non_dict_content(self) -> None:
        validator = DefaultAIResponseValidator()
        with pytest.raises(AIResponseValidationError):
            validator.validate(
                "not a dict", output_format=CopilotOutputFormat.MARKDOWN, raw_text=""
            )

    def test_rejects_empty_dict(self) -> None:
        validator = DefaultAIResponseValidator()
        with pytest.raises(AIResponseValidationError):
            validator.validate({}, output_format=CopilotOutputFormat.MARKDOWN, raw_text="")

    def test_rejects_sections_that_are_all_blank(self) -> None:
        validator = DefaultAIResponseValidator()
        with pytest.raises(AIResponseValidationError):
            validator.validate(
                {"Heading": "   "}, output_format=CopilotOutputFormat.MARKDOWN, raw_text=""
            )


class TestValidateText:
    def test_accepts_non_blank_text(self) -> None:
        validator = DefaultAIResponseValidator()
        validator.validate("hello", output_format=CopilotOutputFormat.TEXT, raw_text="hello")

    def test_rejects_blank_text(self) -> None:
        validator = DefaultAIResponseValidator()
        with pytest.raises(AIResponseValidationError):
            validator.validate("", output_format=CopilotOutputFormat.TEXT, raw_text="   ")

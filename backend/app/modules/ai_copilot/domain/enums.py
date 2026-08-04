"""Enums owned by the AI Clinical Copilot module's domain."""

from enum import StrEnum


class CopilotOutputFormat(StrEnum):
    """What shape the LLM was asked to reply in — drives both
    `infrastructure/parsing/structured_output_parser.py`'s parse strategy
    and `infrastructure/validation/response_validator.py`'s validation
    rules for the resulting `AIResponse.parsed_content`."""

    JSON = "json"
    MARKDOWN = "markdown"
    TEXT = "text"

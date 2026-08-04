"""Unit tests for `PromptRenderer`."""

import pytest

from app.modules.ai.application.dto import PromptVariables
from app.modules.ai.domain.exceptions import InvalidPromptTemplateError, PromptVariableMissingError
from app.modules.ai.domain.value_objects import PromptTemplate
from app.modules.ai.infrastructure.prompts.renderer import PromptRenderer


class TestExtractVariableNames:
    def test_finds_all_placeholders(self) -> None:
        renderer = PromptRenderer()
        names = renderer.extract_variable_names("Hello {{ name }}, you are {{ age }} years old.")
        assert names == frozenset({"name", "age"})

    def test_returns_empty_set_when_no_placeholders(self) -> None:
        renderer = PromptRenderer()
        assert renderer.extract_variable_names("no placeholders here") == frozenset()


class TestRender:
    def test_substitutes_a_single_variable(self) -> None:
        renderer = PromptRenderer()
        template = PromptTemplate(name="greeting", version=1, template_string="Hello {{ name }}!")

        result = renderer.render(template, PromptVariables({"name": "Ada"}))

        assert result == "Hello Ada!"

    def test_substitutes_multiple_occurrences_of_the_same_variable(self) -> None:
        renderer = PromptRenderer()
        template = PromptTemplate(
            name="repeat", version=1, template_string="{{ name }} and {{ name }} again"
        )

        result = renderer.render(template, PromptVariables({"name": "Ada"}))

        assert result == "Ada and Ada again"

    def test_coerces_non_string_values_to_str(self) -> None:
        renderer = PromptRenderer()
        template = PromptTemplate(name="count", version=1, template_string="You have {{ n }} items")

        result = renderer.render(template, PromptVariables({"n": 3}))

        assert result == "You have 3 items"

    def test_raises_when_a_placeholder_has_no_matching_variable(self) -> None:
        renderer = PromptRenderer()
        template = PromptTemplate(name="greeting", version=1, template_string="Hello {{ name }}!")

        with pytest.raises(PromptVariableMissingError):
            renderer.render(template, PromptVariables.empty())

    def test_raises_when_declared_variable_names_are_not_in_the_template_text(self) -> None:
        renderer = PromptRenderer()
        template = PromptTemplate(
            name="greeting",
            version=1,
            template_string="Hello {{ name }}!",
            variable_names=frozenset({"name", "typo_var"}),
        )

        with pytest.raises(InvalidPromptTemplateError):
            renderer.render(template, PromptVariables({"name": "Ada", "typo_var": "x"}))

    def test_extra_supplied_variables_not_in_the_template_are_ignored(self) -> None:
        renderer = PromptRenderer()
        template = PromptTemplate(name="greeting", version=1, template_string="Hello {{ name }}!")

        result = renderer.render(template, PromptVariables({"name": "Ada", "unused": "x"}))

        assert result == "Hello Ada!"

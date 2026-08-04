"""`PromptRenderer` — substitutes `{{ variable_name }}` placeholders in a
`PromptTemplate.template_string` with values from a `PromptVariables`.

A small hand-rolled `{{ name }}` substitution, not Jinja2 — this task's
prompt templates need plain variable interpolation only (no loops,
conditionals, or filters), and avoiding a templating-engine dependency
keeps the AI Foundation's prompt system free of a third-party attack
surface for what is, structurally, untrusted-ish input (prompt text often
originates from configuration, and a full template language would let a
malformed/malicious template do far more than substitute text).

Validates in both directions: every placeholder actually present in
`template_string` must have a matching entry in `variables`
(`PromptVariableMissingError` otherwise), and — since
`PromptTemplate.variable_names` is declared separately from the template
text (see that value object's own docstring) — every name the template
*declares* it needs is cross-checked against what's actually present in
the string, catching a stale `variable_names` declaration.
"""

import re

from app.modules.ai.application.dto import PromptVariables
from app.modules.ai.domain.exceptions import InvalidPromptTemplateError, PromptVariableMissingError
from app.modules.ai.domain.value_objects import PromptTemplate

_PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


class PromptRenderer:
    def extract_variable_names(self, template_string: str) -> frozenset[str]:
        return frozenset(_PLACEHOLDER_PATTERN.findall(template_string))

    def render(self, template: PromptTemplate, variables: PromptVariables) -> str:
        placeholders = self.extract_variable_names(template.template_string)
        missing_from_text = template.variable_names - placeholders
        if missing_from_text:
            raise InvalidPromptTemplateError(
                f"template {template.name!r} v{template.version} declares variable(s) "
                f"{sorted(missing_from_text)} not present in its own template_string"
            )

        for name in placeholders:
            if name not in variables:
                raise PromptVariableMissingError(template.name, name)

        def _substitute(match: re.Match[str]) -> str:
            name = match.group(1)
            value = variables.get(name)
            assert value is not None  # already validated present, above
            return value

        return _PLACEHOLDER_PATTERN.sub(_substitute, template.template_string)

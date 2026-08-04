"""`DefaultAIResponseValidator` — the one concrete
`AIResponseValidatorPort` implementation this task ships.

Deliberately generic, not clinical: this task explicitly excludes any
medical-intelligence feature (SOAP/ICD/prescription/diagnosis generation),
so there is no clinical shape to validate against yet — these checks only
catch "the model returned something structurally unusable" (empty output,
a JSON scalar/`null` where structured content was expected), the same
class of defect every one of AI Foundation's own provider adapters
already guards against for its own layer. A future clinical-feature
module is expected to layer its own schema-specific validation on top
of, not instead of, this generic pass.
"""

from app.modules.ai_copilot.application.ports import AIResponseValidatorPort
from app.modules.ai_copilot.domain.enums import CopilotOutputFormat
from app.modules.ai_copilot.domain.exceptions import AIResponseValidationError


class DefaultAIResponseValidator(AIResponseValidatorPort):
    def validate(
        self, parsed_content: object, *, output_format: CopilotOutputFormat, raw_text: str
    ) -> None:
        if output_format is CopilotOutputFormat.JSON:
            self._validate_json(parsed_content)
        elif output_format is CopilotOutputFormat.MARKDOWN:
            self._validate_markdown(parsed_content)
        else:
            self._validate_text(raw_text)

    def _validate_json(self, parsed_content: object) -> None:
        if parsed_content is None:
            raise AIResponseValidationError("JSON response was null")
        if isinstance(parsed_content, dict | list) and len(parsed_content) == 0:
            raise AIResponseValidationError("JSON response was empty")

    def _validate_markdown(self, parsed_content: object) -> None:
        if not isinstance(parsed_content, dict) or not parsed_content:
            raise AIResponseValidationError("Markdown response produced no sections")
        if all(not body.strip() for body in parsed_content.values()):
            raise AIResponseValidationError("every Markdown section was empty")

    def _validate_text(self, raw_text: str) -> None:
        if not raw_text.strip():
            raise AIResponseValidationError("text response was blank")

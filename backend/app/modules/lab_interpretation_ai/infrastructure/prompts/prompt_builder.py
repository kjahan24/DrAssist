"""`DefaultLabPromptBuilder` — the one concrete `LabPromptBuilderPort`
implementation this task ships: renders a `LabInterpretationTemplateSet`'s
three templates via AI Foundation's public `AIGatewayPort.render_prompt`,
turning `LabInterpretationInput`'s fields into the flat string
`PromptVariables` the renderer needs.
"""

from app.modules.ai.public.dto import AIMessage, AIMessageRole, PromptVariables
from app.modules.ai.public.interfaces import AIGatewayPort
from app.modules.lab_interpretation_ai.application.ports import LabPromptBuilderPort
from app.modules.lab_interpretation_ai.domain.value_objects import (
    LabInterpretationInput,
    LabInterpretationTemplateSet,
    LabValue,
)

_NOT_PROVIDED = "Not provided."


def _join_or_default(items: tuple[str, ...]) -> str:
    return ", ".join(items) if items else _NOT_PROVIDED


def _text_or_default(value: str | None) -> str:
    return value.strip() if value and value.strip() else _NOT_PROVIDED


def _format_lab_value(lab_value: LabValue) -> str:
    parts = [lab_value.test_name, lab_value.value]
    if lab_value.unit:
        parts.append(lab_value.unit)
    line = " ".join(parts)
    if lab_value.reference_range:
        line += f" (ref: {lab_value.reference_range})"
    return line


def _format_lab_values(lab_values: tuple[LabValue, ...]) -> str:
    if not lab_values:
        return _NOT_PROVIDED
    return "; ".join(_format_lab_value(lab_value) for lab_value in lab_values)


class DefaultLabPromptBuilder(LabPromptBuilderPort):
    def __init__(self, *, ai_gateway: AIGatewayPort) -> None:
        self._ai_gateway = ai_gateway

    def build_variables(self, input_dto: LabInterpretationInput) -> PromptVariables:
        return PromptVariables(
            {
                "language": input_dto.language,
                "lab_values": _format_lab_values(input_dto.lab_values),
                "patient_age": str(input_dto.patient_age)
                if input_dto.patient_age is not None
                else _NOT_PROVIDED,
                "patient_sex": input_dto.patient_sex.value
                if input_dto.patient_sex is not None
                else _NOT_PROVIDED,
                "pregnancy_status": input_dto.pregnancy_status.value
                if input_dto.pregnancy_status is not None
                else _NOT_PROVIDED,
                "visit_type": _text_or_default(input_dto.visit_type),
                "medical_conditions": _join_or_default(input_dto.medical_conditions),
                "allergies": _join_or_default(input_dto.allergies),
                "medications": _join_or_default(input_dto.medications),
                "clinical_notes": _join_or_default(input_dto.clinical_notes),
                "soap_notes": _join_or_default(input_dto.soap_notes),
            }
        )

    async def build_messages(
        self, input_dto: LabInterpretationInput, template_set: LabInterpretationTemplateSet
    ) -> list[AIMessage]:
        variables = self.build_variables(input_dto)
        system_text = await self._ai_gateway.render_prompt(
            template_set.system_template_name, variables, version=template_set.version
        )
        developer_text = await self._ai_gateway.render_prompt(
            template_set.developer_template_name, variables, version=template_set.version
        )
        user_text = await self._ai_gateway.render_prompt(
            template_set.user_template_name, variables, version=template_set.version
        )
        return [
            AIMessage(role=AIMessageRole.SYSTEM, content=system_text),
            AIMessage(role=AIMessageRole.SYSTEM, content=developer_text),
            AIMessage(role=AIMessageRole.USER, content=user_text),
        ]

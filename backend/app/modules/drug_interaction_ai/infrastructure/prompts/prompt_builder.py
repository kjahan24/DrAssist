"""`DefaultDrugSafetyAnalysisPromptBuilder` — the one concrete
`DrugSafetyAnalysisPromptBuilderPort` implementation this task ships:
renders a `DrugInteractionTemplateSet`'s three templates via AI
Foundation's public `AIGatewayPort.render_prompt`, turning
`DrugInteractionAnalysisInput`'s fields into the flat string
`PromptVariables` the renderer needs.
"""

from app.modules.ai.public.dto import AIMessage, AIMessageRole, PromptVariables
from app.modules.ai.public.interfaces import AIGatewayPort
from app.modules.drug_interaction_ai.application.ports import DrugSafetyAnalysisPromptBuilderPort
from app.modules.drug_interaction_ai.domain.value_objects import (
    DrugInteractionAnalysisInput,
    DrugInteractionTemplateSet,
    MedicationEntry,
)

_NOT_PROVIDED = "Not provided."


def _join_or_default(items: tuple[str, ...]) -> str:
    return ", ".join(items) if items else _NOT_PROVIDED


def _text_or_default(value: str | None) -> str:
    return value.strip() if value and value.strip() else _NOT_PROVIDED


def _format_medication(medication: MedicationEntry) -> str:
    parts = [medication.drug_name]
    if medication.generic_name:
        parts.append(f"({medication.generic_name})")
    if medication.dose:
        parts.append(medication.dose)
    if medication.route:
        parts.append(medication.route)
    if medication.frequency:
        parts.append(medication.frequency)
    if medication.duration:
        parts.append(f"for {medication.duration}")
    return " ".join(parts)


def _format_medications(medications: tuple[MedicationEntry, ...]) -> str:
    if not medications:
        return _NOT_PROVIDED
    return "; ".join(_format_medication(medication) for medication in medications)


class DefaultDrugSafetyAnalysisPromptBuilder(DrugSafetyAnalysisPromptBuilderPort):
    def __init__(self, *, ai_gateway: AIGatewayPort) -> None:
        self._ai_gateway = ai_gateway

    def build_variables(self, input_dto: DrugInteractionAnalysisInput) -> PromptVariables:
        return PromptVariables(
            {
                "language": input_dto.language,
                "current_medications": _format_medications(input_dto.current_medications),
                "new_prescription": _format_medication(input_dto.new_prescription)
                if input_dto.new_prescription is not None
                else _NOT_PROVIDED,
                "diagnosis": _text_or_default(input_dto.diagnosis),
                "problem_list": _join_or_default(input_dto.problem_list),
                "allergies": _join_or_default(input_dto.allergies),
                "medical_conditions": _join_or_default(input_dto.medical_conditions),
                "pregnancy_status": input_dto.pregnancy_status.value
                if input_dto.pregnancy_status is not None
                else _NOT_PROVIDED,
                "lactation_status": input_dto.lactation_status.value
                if input_dto.lactation_status is not None
                else _NOT_PROVIDED,
                "patient_age": str(input_dto.patient_age)
                if input_dto.patient_age is not None
                else _NOT_PROVIDED,
                "patient_weight_kg": str(input_dto.patient_weight_kg)
                if input_dto.patient_weight_kg is not None
                else _NOT_PROVIDED,
                "renal_function": _text_or_default(input_dto.renal_function),
                "hepatic_function": _text_or_default(input_dto.hepatic_function),
                "recent_lab_values": _join_or_default(input_dto.recent_lab_values),
            }
        )

    async def build_messages(
        self, input_dto: DrugInteractionAnalysisInput, template_set: DrugInteractionTemplateSet
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

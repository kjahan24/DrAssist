"""`DefaultDifferentialDiagnosisPromptBuilder` — the one concrete
`DifferentialDiagnosisPromptBuilderPort` implementation this task ships:
renders a `DifferentialDiagnosisTemplateSet`'s three templates via AI
Foundation's public `AIGatewayPort.render_prompt`, turning
`DifferentialDiagnosisInput`'s fields into the flat string
`PromptVariables` the renderer needs.
"""

from app.modules.ai.public.dto import AIMessage, AIMessageRole, PromptVariables
from app.modules.ai.public.interfaces import AIGatewayPort
from app.modules.differential_diagnosis_ai.application.ports import (
    DifferentialDiagnosisPromptBuilderPort,
)
from app.modules.differential_diagnosis_ai.domain.value_objects import (
    DifferentialDiagnosisInput,
    DifferentialDiagnosisTemplateSet,
)

_NOT_PROVIDED = "Not provided."


def _join_or_default(items: tuple[str, ...]) -> str:
    return ", ".join(items) if items else _NOT_PROVIDED


def _text_or_default(value: str | None) -> str:
    return value.strip() if value and value.strip() else _NOT_PROVIDED


def _format_vitals(vitals: dict[str, str]) -> str:
    if not vitals:
        return _NOT_PROVIDED
    return ", ".join(f"{key}: {value}" for key, value in vitals.items())


class DefaultDifferentialDiagnosisPromptBuilder(DifferentialDiagnosisPromptBuilderPort):
    def __init__(self, *, ai_gateway: AIGatewayPort) -> None:
        self._ai_gateway = ai_gateway

    def build_variables(self, evidence: DifferentialDiagnosisInput) -> PromptVariables:
        return PromptVariables(
            {
                "language": evidence.language,
                "patient_age": str(evidence.patient_age)
                if evidence.patient_age is not None
                else _NOT_PROVIDED,
                "patient_sex": evidence.patient_sex.value
                if evidence.patient_sex is not None
                else _NOT_PROVIDED,
                "pregnancy_status": evidence.pregnancy_status.value
                if evidence.pregnancy_status is not None
                else _NOT_PROVIDED,
                "visit_type": _text_or_default(evidence.visit_type),
                "chief_complaint": evidence.chief_complaint,
                "history_of_present_illness": _text_or_default(evidence.history_of_present_illness),
                "symptoms": _join_or_default(evidence.symptoms),
                "review_of_systems": _text_or_default(evidence.review_of_systems),
                "physical_examination": _text_or_default(evidence.physical_examination),
                "vitals": _format_vitals(dict(evidence.vitals)),
                "laboratory_results": _join_or_default(evidence.laboratory_results),
                "imaging_summary": _text_or_default(evidence.imaging_summary),
                "clinical_note": _text_or_default(evidence.clinical_note),
                "soap_note": _text_or_default(evidence.soap_note),
                "icd10_suggestions": _join_or_default(evidence.icd10_suggestions),
                "prescription_suggestions": _join_or_default(evidence.prescription_suggestions),
                "allergies": _join_or_default(evidence.allergies),
                "medical_conditions": _join_or_default(evidence.medical_conditions),
            }
        )

    async def build_messages(
        self, evidence: DifferentialDiagnosisInput, template_set: DifferentialDiagnosisTemplateSet
    ) -> list[AIMessage]:
        variables = self.build_variables(evidence)
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

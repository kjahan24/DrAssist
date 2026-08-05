"""`DefaultRiskStratificationAnalysisPromptBuilder` — the one concrete
`RiskStratificationAnalysisPromptBuilderPort` implementation this task
ships: renders a `RiskStratificationTemplateSet`'s three templates via
AI Foundation's public `AIGatewayPort.render_prompt`, turning
`RiskStratificationInput`'s fields into the flat string `PromptVariables`
the renderer needs.
"""

from app.modules.ai.public.dto import AIMessage, AIMessageRole, PromptVariables
from app.modules.ai.public.interfaces import AIGatewayPort
from app.modules.risk_stratification_ai.application.ports import (
    RiskStratificationAnalysisPromptBuilderPort,
)
from app.modules.risk_stratification_ai.domain.value_objects import (
    LabValue,
    RiskStratificationInput,
    RiskStratificationTemplateSet,
    VitalSigns,
)

_NOT_PROVIDED = "Not provided."


def _join_or_default(items: tuple[str, ...]) -> str:
    return ", ".join(items) if items else _NOT_PROVIDED


def _format_lab_value(lab: LabValue) -> str:
    reported = lab.value if lab.value and lab.value.strip() else None
    if reported is not None and lab.numeric_value is not None:
        return f"{lab.test_name}: {reported} ({lab.numeric_value:g})"
    if reported is not None:
        return f"{lab.test_name}: {reported}"
    return f"{lab.test_name}: {lab.numeric_value:g}"


def _format_lab_values(lab_values: tuple[LabValue, ...]) -> str:
    if not lab_values:
        return _NOT_PROVIDED
    return "; ".join(_format_lab_value(lab) for lab in lab_values)


def _format_vital_signs(vital_signs: VitalSigns) -> str:
    parts: list[str] = []
    if vital_signs.respiratory_rate is not None:
        parts.append(f"RR {vital_signs.respiratory_rate}/min")
    if vital_signs.oxygen_saturation is not None:
        oxygen_note = " on supplemental oxygen" if vital_signs.on_supplemental_oxygen else ""
        parts.append(f"SpO2 {vital_signs.oxygen_saturation:g}%{oxygen_note}")
    if vital_signs.temperature_celsius is not None:
        parts.append(f"Temp {vital_signs.temperature_celsius:g}C")
    if vital_signs.systolic_bp is not None and vital_signs.diastolic_bp is not None:
        parts.append(f"BP {vital_signs.systolic_bp}/{vital_signs.diastolic_bp} mmHg")
    elif vital_signs.systolic_bp is not None:
        parts.append(f"Systolic BP {vital_signs.systolic_bp} mmHg")
    if vital_signs.heart_rate is not None:
        parts.append(f"HR {vital_signs.heart_rate}/min")
    if vital_signs.consciousness_level is not None:
        parts.append(f"AVPU {vital_signs.consciousness_level.value}")
    return ", ".join(parts) if parts else _NOT_PROVIDED


class DefaultRiskStratificationAnalysisPromptBuilder(RiskStratificationAnalysisPromptBuilderPort):
    def __init__(self, *, ai_gateway: AIGatewayPort) -> None:
        self._ai_gateway = ai_gateway

    def build_variables(self, input_dto: RiskStratificationInput) -> PromptVariables:
        return PromptVariables(
            {
                "language": input_dto.language,
                "patient_age": str(input_dto.patient_age)
                if input_dto.patient_age is not None
                else _NOT_PROVIDED,
                "vital_signs": _format_vital_signs(input_dto.vital_signs),
                "lab_values": _format_lab_values(input_dto.lab_values),
                "medical_history": _join_or_default(input_dto.medical_history),
                "diagnoses": _join_or_default(input_dto.diagnoses),
                "current_medications": _join_or_default(input_dto.current_medications),
                "allergies": _join_or_default(input_dto.allergies),
                "clinical_notes": _join_or_default(input_dto.clinical_notes),
                "soap_notes": _join_or_default(input_dto.soap_notes),
                "laboratory_interpretation": input_dto.laboratory_interpretation or _NOT_PROVIDED,
                "radiology_interpretation": input_dto.radiology_interpretation or _NOT_PROVIDED,
                "pathology_interpretation": input_dto.pathology_interpretation or _NOT_PROVIDED,
                "medical_reasoning_context": input_dto.medical_reasoning_context or _NOT_PROVIDED,
            }
        )

    async def build_messages(
        self,
        input_dto: RiskStratificationInput,
        template_set: RiskStratificationTemplateSet,
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

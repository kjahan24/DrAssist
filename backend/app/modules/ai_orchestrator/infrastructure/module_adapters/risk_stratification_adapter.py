"""`RiskStratificationWorkflowAdapter` — the `WorkflowExecutorPort`
implementation for `WorkflowModule.RISK_STRATIFICATION`, wrapping
`app.modules.risk_stratification_ai`'s own public facade. See this
package's own `__init__.py` for the shape every adapter in this package
shares.

`bundle.vital_signs` is a generic `Mapping[str, str]` (this
orchestrator's own uniform vitals shape, matching several peer modules'
own `vitals: Mapping[str, str]` fields directly) while
`RiskStratificationInput.vital_signs` needs a real, typed `VitalSigns`
value object — `_parse_vital_signs` below best-effort-parses a small,
documented set of known key spellings (case-insensitive) into that
shape, silently skipping (never raising, never fabricating a value for)
any key it does not recognize or any value it cannot parse as the
expected type. When none of the given keys are recognized, the
resulting `VitalSigns` is empty and this step's own
`check_prerequisites` reports it as a missing prerequisite (that peer
module's own `RiskStratificationInput` requires at least one vital sign
to be set at all).
"""

from collections.abc import Mapping
from time import perf_counter

from app.modules.ai_orchestrator.application.ports import WorkflowExecutorPort
from app.modules.ai_orchestrator.domain.enums import WorkflowModule, WorkflowStepStatus
from app.modules.ai_orchestrator.domain.value_objects import (
    WorkflowExecutionInput,
    WorkflowStepResult,
)
from app.modules.ai_orchestrator.infrastructure.module_adapters._common import upstream_summary
from app.modules.risk_stratification_ai.public.dto import (
    ConsciousnessLevel,
    LabValue,
    RiskStratificationInput,
    RiskStratificationSetting,
    VitalSigns,
)
from app.modules.risk_stratification_ai.public.interfaces import RiskStratificationAIPort

_RESPIRATORY_RATE_KEYS = ("respiratory_rate", "rr")
_OXYGEN_SATURATION_KEYS = ("oxygen_saturation", "spo2")
_SUPPLEMENTAL_OXYGEN_KEYS = ("on_supplemental_oxygen", "supplemental_oxygen")
_TEMPERATURE_KEYS = ("temperature_celsius", "temperature", "temp")
_SYSTOLIC_BP_KEYS = ("systolic_bp", "sbp")
_DIASTOLIC_BP_KEYS = ("diastolic_bp", "dbp")
_HEART_RATE_KEYS = ("heart_rate", "hr", "pulse")
_CONSCIOUSNESS_KEYS = ("consciousness_level", "avpu")
_TRUE_STRINGS = frozenset({"true", "yes", "1", "on"})


def _find(vital_signs: Mapping[str, str], keys: tuple[str, ...]) -> str | None:
    lowered = {key.lower(): value for key, value in vital_signs.items()}
    for key in keys:
        if key in lowered:
            return lowered[key]
    return None


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def _parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    return value.strip().lower() in _TRUE_STRINGS


def _parse_consciousness_level(value: str | None) -> ConsciousnessLevel | None:
    if value is None:
        return None
    try:
        return ConsciousnessLevel(value.strip().lower())
    except ValueError:
        return None


def parse_vital_signs(vital_signs: Mapping[str, str]) -> VitalSigns:
    return VitalSigns(
        respiratory_rate=_parse_int(_find(vital_signs, _RESPIRATORY_RATE_KEYS)),
        oxygen_saturation=_parse_float(_find(vital_signs, _OXYGEN_SATURATION_KEYS)),
        on_supplemental_oxygen=_parse_bool(_find(vital_signs, _SUPPLEMENTAL_OXYGEN_KEYS)),
        temperature_celsius=_parse_float(_find(vital_signs, _TEMPERATURE_KEYS)),
        systolic_bp=_parse_int(_find(vital_signs, _SYSTOLIC_BP_KEYS)),
        diastolic_bp=_parse_int(_find(vital_signs, _DIASTOLIC_BP_KEYS)),
        heart_rate=_parse_int(_find(vital_signs, _HEART_RATE_KEYS)),
        consciousness_level=_parse_consciousness_level(_find(vital_signs, _CONSCIOUSNESS_KEYS)),
    )


class RiskStratificationWorkflowAdapter(WorkflowExecutorPort):
    def __init__(self, *, facade: RiskStratificationAIPort) -> None:
        self._facade = facade

    @property
    def module(self) -> WorkflowModule:
        return WorkflowModule.RISK_STRATIFICATION

    def check_prerequisites(self, bundle: WorkflowExecutionInput) -> tuple[str, ...]:
        if parse_vital_signs(bundle.vital_signs).is_empty:
            return ("no parseable vital signs were provided",)
        return ()

    async def execute(
        self, bundle: WorkflowExecutionInput, context: Mapping[WorkflowModule, str]
    ) -> WorkflowStepResult:
        start = perf_counter()
        lab_values = tuple(
            LabValue(test_name=f"Finding {index + 1}", value=finding)
            for index, finding in enumerate(bundle.laboratory_findings)
        )
        input_dto = RiskStratificationInput(
            organization_id=bundle.organization_id,
            patient_id=bundle.patient_id,
            risk_setting=RiskStratificationSetting.OUTPATIENT,
            vital_signs=parse_vital_signs(bundle.vital_signs),
            lab_values=lab_values,
            patient_age=bundle.patient_age,
            medical_history=bundle.diagnoses,
            diagnoses=bundle.diagnoses,
            current_medications=bundle.medication_list,
            language=bundle.language,
            laboratory_interpretation=upstream_summary(context, WorkflowModule.LAB_INTERPRETATION),
            radiology_interpretation=upstream_summary(
                context, WorkflowModule.RADIOLOGY_INTERPRETATION
            ),
            pathology_interpretation=upstream_summary(
                context, WorkflowModule.PATHOLOGY_INTERPRETATION
            ),
            medical_reasoning_context=upstream_summary(context, WorkflowModule.MEDICAL_REASONING),
        )
        generated = await self._facade.analyze_patient_risk(input_dto)
        latency_ms = (perf_counter() - start) * 1000
        return WorkflowStepResult(
            module=self.module,
            status=WorkflowStepStatus.COMPLETED,
            summary=generated.result.raw_text,
            confidence_score=generated.result.confidence_score,
            latency_ms=latency_ms,
        )

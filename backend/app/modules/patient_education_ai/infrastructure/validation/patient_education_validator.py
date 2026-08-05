"""`DefaultPatientEducationAnalysisValidator` — the one concrete
`PatientEducationAnalysisValidatorPort` implementation this task ships,
per this task's own "malformed JSON, hallucinated recommendations,
unsafe instructions, invalid confidence" VALIDATION categories
("malformed JSON" is `PatientEducationAnalysisParserPort`'s concern, and
"missing diagnosis"/"missing medication list" are `domain
/value_objects.py`'s own `__post_init__` concern on the caller-supplied
*input* — a result that reaches this validator already parsed
successfully, so only content-level checks on the AI's own *output*
remain here, the same split every prior AI module's own validator
documents for itself).

Checks run in this order, each a distinct failure mode with its own
domain exception:

1. Any curated unsafe-instruction phrase (see `_UNSAFE_PHRASES`) found
   in `medication_instructions`, `home_care_plan`,
   `emergency_instructions`, or `warning_signs` ->
   `UnsafeInstructionError` — the sharpest-edged check this validator
   performs, per this task's own GOAL section ("MUST NOT replace
   physician counselling"); checked first because an unsafe instruction
   is a more urgent failure than a stylistic hallucination placeholder.
2. `confidence_score` present but outside `[0.0, 1.0]` ->
   `InvalidPatientEducationConfidenceValueError`. `None` is not an
   error here: this module's confidence is always deterministically
   filled in by `MedicalReasoningAIPort.score_confidence` during
   enrichment (see `application/use_cases
   /generate_patient_education.py`), so a missing AI-reported value is
   expected, not invalid.
3. Any hallucinated placeholder in `patient_summary`,
   `diagnosis_explanation`, or any of the ten list-shaped OUTPUT fields
   -> `HallucinatedRecommendationError`.
"""

from app.modules.patient_education_ai.application.ports import (
    PatientEducationAnalysisValidatorPort,
)
from app.modules.patient_education_ai.domain.exceptions import (
    HallucinatedRecommendationError,
    InvalidPatientEducationConfidenceValueError,
    UnsafeInstructionError,
)
from app.modules.patient_education_ai.domain.value_objects import (
    PatientEducationInput,
    PatientEducationResult,
)
from app.shared.infrastructure.text_processing.placeholder_detection import (
    find_placeholder_marker,
)

_UNSAFE_PHRASES: tuple[str, ...] = (
    "double the dose",
    "double your dose",
    "stop taking all medications",
    "stop all your medications",
    "stop all medications",
    "no need to see a doctor",
    "don't need to see a doctor",
    "do not need to see a doctor",
    "ignore your doctor",
    "increase your dose without",
    "do not seek emergency care",
    "avoid the emergency room",
    "no need to go to the hospital",
    "you don't need emergency care",
)

_UNSAFE_CHECKED_FIELDS = (
    "medication_instructions",
    "home_care_plan",
    "emergency_instructions",
    "warning_signs",
)


class DefaultPatientEducationAnalysisValidator(PatientEducationAnalysisValidatorPort):
    def validate(self, result: PatientEducationResult, input_dto: PatientEducationInput) -> None:
        self._check_unsafe_instructions(result)
        self._check_confidence_value(result)
        self._check_hallucinated_placeholders(result)

    def _check_unsafe_instructions(self, result: PatientEducationResult) -> None:
        field_values = {
            "medication_instructions": result.medication_instructions,
            "home_care_plan": result.home_care_plan,
            "emergency_instructions": result.emergency_instructions,
            "warning_signs": result.warning_signs,
        }
        for field_name in _UNSAFE_CHECKED_FIELDS:
            for text in field_values[field_name]:
                normalized = text.lower()
                for phrase in _UNSAFE_PHRASES:
                    if phrase in normalized:
                        raise UnsafeInstructionError(field_name, phrase)

    def _check_confidence_value(self, result: PatientEducationResult) -> None:
        if result.confidence_score is not None and not (0.0 <= result.confidence_score <= 1.0):
            raise InvalidPatientEducationConfidenceValueError()

    def _check_hallucinated_placeholders(self, result: PatientEducationResult) -> None:
        text_fields = (
            ("patient_summary", result.patient_summary),
            ("diagnosis_explanation", result.diagnosis_explanation),
        )
        for field_name, text in text_fields:
            placeholder = find_placeholder_marker(text)
            if placeholder is not None:
                raise HallucinatedRecommendationError(field_name, placeholder)

        list_fields = (
            ("medication_instructions", result.medication_instructions),
            ("home_care_plan", result.home_care_plan),
            ("lifestyle_advice", result.lifestyle_advice),
            ("diet_advice", result.diet_advice),
            ("exercise_advice", result.exercise_advice),
            ("warning_signs", result.warning_signs),
            ("emergency_instructions", result.emergency_instructions),
            ("follow_up_plan", result.follow_up_plan),
            ("patient_checklist", result.patient_checklist),
        )
        for field_name, items in list_fields:
            for text in items:
                placeholder = find_placeholder_marker(text)
                if placeholder is not None:
                    raise HallucinatedRecommendationError(field_name, placeholder)

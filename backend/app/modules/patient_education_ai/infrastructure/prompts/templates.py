"""Production prompt templates for the AI Patient Education & Discharge
Instructions module — one `(system, developer, user)` triple per
`PatientEducationSetting`, each independently versioned, registered
into AI Foundation's shared `PromptRegistry` by `template_registrar.py`.

Imports AI Foundation's `domain.value_objects.PromptTemplate` directly
(not `.public`) — the same justified exception every prior AI module's
own `infrastructure/prompts/templates.py` module docstring documents in
full: constructing instances of it to register is exactly the mechanism
`app.modules.ai.container.get_prompt_registry`'s own docstring
anticipates and names for this purpose; nothing in AI Foundation's own
source is modified.

Template names are prefixed `patient_education` — no pre-existing,
persisted sibling module shares this name (confirmed by directory
search before this phase began), so no further disambiguation is
needed.

Every `developer` template carries the same fixed JSON-output contract —
`patient_summary`, `diagnosis_explanation`, `medication_instructions`,
`home_care_plan`, `lifestyle_advice`, `diet_advice`, `exercise_advice`,
`warning_signs`, `emergency_instructions`, `follow_up_plan`,
`patient_checklist`, and `confidence_score` — matching this task's own
OUTPUT specification field-for-field. `system` templates carry
setting-specific tone/reading-level guidance across this task's own six
settings (adult/pediatric/geriatric/pregnancy/emergency_discharge/
hospital_discharge); `user` templates are the diagnosis/medication/
patient-context placeholders `infrastructure/prompts/prompt_builder.py`
fills in. This module provides patient education support only — every
template is explicit that it never replaces physician counselling and
never gives directive medical orders beyond what the given clinical
context supports, per this task's own GOAL section.
"""

from app.modules.ai.domain.value_objects import PromptTemplate
from app.modules.patient_education_ai.domain.enums import PatientEducationSetting

_JSON_CONTRACT = (
    "You must respond with ONLY a single JSON object and nothing else — "
    "no markdown code fences, no prose before or after it. You provide "
    "patient education support only — you never replace physician "
    "counselling and you never give a directive medical order beyond "
    "what the clinical context given to you supports. Write every field "
    "in clear, plain language a patient without medical training can "
    "understand. The JSON object must have exactly these twelve "
    'keys:\n\n"patient_summary" (a short, friendly overview of the '
    'visit or admission), "diagnosis_explanation" (a plain-language '
    'explanation of the diagnosis or diagnoses), "medication_instructions", '
    '"home_care_plan", "lifestyle_advice", "diet_advice", '
    '"exercise_advice", "warning_signs", "emergency_instructions", '
    '"follow_up_plan", and "patient_checklist" (each a JSON array of '
    "strings, with no duplicate entries within the same array), and "
    '"confidence_score" (a number between 0.0 and 1.0). Only include '
    "instructions clearly supported by the diagnoses, medications, and "
    "clinical context given to you — never invent a diagnosis, "
    "medication, or instruction that was not provided or reasonably "
    "inferable from it, and never suggest a dose change, stopping a "
    "medication, or delaying emergency care. Do not include placeholder "
    'text such as "[insert]", "TBD", "XXX", or "Lorem ipsum" anywhere in '
    "your response."
)

_USER_TEMPLATE = (
    "Patient education request:\n\n"
    "Patient Age: {{ patient_age }}\n"
    "Diagnoses: {{ diagnoses }}\n"
    "Current Medications: {{ current_medications }}\n\n"
    "Clinical Notes: {{ clinical_notes }}\n"
    "SOAP Notes: {{ soap_notes }}\n\n"
    "Prescription AI Output: {{ prescription_ai_output }}\n"
    "Drug Interaction AI Output: {{ drug_interaction_ai_output }}\n"
    "Risk Stratification AI Output: {{ risk_stratification_ai_output }}\n"
    "Laboratory Interpretation: {{ laboratory_interpretation }}\n"
    "Radiology Interpretation: {{ radiology_interpretation }}\n"
    "Pathology Interpretation: {{ pathology_interpretation }}\n"
    "Medical Reasoning Context: {{ medical_reasoning_context }}\n"
    "Differential Diagnosis Context: {{ differential_diagnosis_context }}\n\n"
    "Produce patient-friendly education material and discharge "
    "instructions now."
)

_USER_TEMPLATE_VARIABLES = frozenset(
    {
        "patient_age",
        "diagnoses",
        "current_medications",
        "clinical_notes",
        "soap_notes",
        "prescription_ai_output",
        "drug_interaction_ai_output",
        "risk_stratification_ai_output",
        "laboratory_interpretation",
        "radiology_interpretation",
        "pathology_interpretation",
        "medical_reasoning_context",
        "differential_diagnosis_context",
    }
)

_SYSTEM_TEMPLATE_VARIABLES = frozenset({"language"})

_STYLE_GUIDANCE: dict[PatientEducationSetting, str] = {
    PatientEducationSetting.ADULT: (
        "You are an expert patient education engine producing "
        "plain-language educational material in {{ language }}, "
        "appropriate for a general adult patient. Ground every "
        "instruction in the diagnoses and medications given to you."
    ),
    PatientEducationSetting.PEDIATRIC: (
        "You are an expert patient education engine producing "
        "plain-language educational material in {{ language }}, "
        "appropriate for a caregiver of a pediatric patient — address "
        "the caregiver directly, use simple language, and explicitly "
        "flag anything that presents differently or needs closer "
        "attention in children."
    ),
    PatientEducationSetting.GERIATRIC: (
        "You are an expert patient education engine producing "
        "plain-language educational material in {{ language }}, "
        "appropriate for a geriatric patient — use larger, simpler "
        "steps, consider polypharmacy and fall risk, and involve a "
        "caregiver where appropriate."
    ),
    PatientEducationSetting.PREGNANCY: (
        "You are an expert patient education engine producing "
        "plain-language educational material in {{ language }}, "
        "appropriate for a pregnant or postpartum patient — weigh "
        "pregnancy and lactation safety carefully for every "
        "recommendation you make."
    ),
    PatientEducationSetting.EMERGENCY_DISCHARGE: (
        "You are an expert patient education engine producing "
        "plain-language educational material in {{ language }}, "
        "appropriate for a patient being discharged from the emergency "
        "department — prioritize clear warning signs and emergency "
        "instructions for when to return immediately."
    ),
    PatientEducationSetting.HOSPITAL_DISCHARGE: (
        "You are an expert patient education engine producing "
        "plain-language educational material in {{ language }}, "
        "appropriate for a patient being discharged from an inpatient "
        "admission — prioritize a complete home care plan and "
        "follow-up plan covering the full admission."
    ),
}


def system_template_name(education_setting: PatientEducationSetting) -> str:
    return f"patient_education.{education_setting.value}.system"


def developer_template_name(education_setting: PatientEducationSetting) -> str:
    return f"patient_education.{education_setting.value}.developer"


def user_template_name(education_setting: PatientEducationSetting) -> str:
    return f"patient_education.{education_setting.value}.user"


def build_all_templates(*, version: int = 1) -> list[PromptTemplate]:
    """Constructs the full 18-template set (6 settings x system/
    developer/user) at the given version — called once by
    `template_registrar.py`."""
    templates: list[PromptTemplate] = []
    for education_setting, guidance in _STYLE_GUIDANCE.items():
        templates.append(
            PromptTemplate(
                name=system_template_name(education_setting),
                version=version,
                template_string=guidance,
                variable_names=_SYSTEM_TEMPLATE_VARIABLES,
                description=f"System prompt for {education_setting.value} patient education.",
            )
        )
        templates.append(
            PromptTemplate(
                name=developer_template_name(education_setting),
                version=version,
                template_string=_JSON_CONTRACT,
                variable_names=frozenset(),
                description=(
                    f"JSON output contract for {education_setting.value} patient education."
                ),
            )
        )
        templates.append(
            PromptTemplate(
                name=user_template_name(education_setting),
                version=version,
                template_string=_USER_TEMPLATE,
                variable_names=_USER_TEMPLATE_VARIABLES,
                description=(
                    f"Clinical context prompt for {education_setting.value} patient education."
                ),
            )
        )
    return templates

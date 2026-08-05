"""Production prompt templates for the AI Risk Stratification & Early
Warning Score module — one `(system, developer, user)` triple per
`RiskStratificationSetting`, each independently versioned, registered
into AI Foundation's shared `PromptRegistry` by `template_registrar.py`.

Imports AI Foundation's `domain.value_objects.PromptTemplate` directly
(not `.public`) — the same justified exception every prior AI module's
own `infrastructure/prompts/templates.py` module docstring documents in
full: constructing instances of it to register is exactly the mechanism
`app.modules.ai.container.get_prompt_registry`'s own docstring
anticipates and names for this purpose; nothing in AI Foundation's own
source is modified.

Template names are prefixed `risk_stratification` — no pre-existing,
persisted sibling module shares this name (confirmed by directory
search before this phase began), so no further disambiguation is
needed.

Every `developer` template carries the same fixed JSON-output contract —
`overall_risk_level`, `risk_scores` (an array of `{category, score_value,
contributing_factors, clinical_explanation}` objects — this task's own
"Risk Scores"/"Risk Category"/"Contributing Factors"/"Clinical
Explanation" OUTPUT fields are all represented on this one array's
items, per `RiskStratificationResult`'s own docstring),
`early_warning_indicators`, `recommended_monitoring`,
`suggested_escalation`, `suggested_follow_up`, `red_flag_alerts`,
`clinical_reasoning`, and `confidence_score` — matching this task's own
OUTPUT specification field-for-field. `system` templates carry
setting-specific tone/priority guidance across this task's own six
settings (emergency/inpatient/icu/outpatient/pediatric/geriatric); `user`
templates are the vital-signs/lab-values/patient-context placeholders
`infrastructure/prompts/prompt_builder.py` fills in. This module
provides clinical risk assessment and early-deterioration decision
support only — every template is explicit that it never autonomously
makes medical decisions and never replaces physician judgment, per this
task's own GOAL section.
"""

from app.modules.ai.domain.value_objects import PromptTemplate
from app.modules.risk_stratification_ai.domain.enums import RiskStratificationSetting

_JSON_CONTRACT = (
    "You must respond with ONLY a single JSON object and nothing else — "
    "no markdown code fences, no prose before or after it. You provide "
    "clinical risk assessment and early deterioration decision support "
    "only — you never autonomously make medical decisions and you never "
    "replace physician judgment. The JSON object must have exactly these "
    "nine keys:\n\n"
    '"overall_risk_level" (exactly one of "low", "moderate", "high", or '
    '"critical"), "risk_scores" (a JSON array of objects, one per '
    'assessed risk, each with "category" — exactly one of "news2", '
    '"mews", "qsofa", "sofa_simplified", "sepsis_risk", "aki_risk", '
    '"respiratory_deterioration", "cardiovascular_risk", "stroke_risk", '
    '"bleeding_risk", "fall_risk", "readmission_risk", "mortality_risk", '
    'or "general_clinical_deterioration" — "score_value" (a number, or '
    'null when the category has no numeric score), "contributing_factors" '
    '(a JSON array of strings), and "clinical_explanation" (a string)), '
    '"early_warning_indicators", "recommended_monitoring", '
    '"suggested_escalation", "suggested_follow_up", and '
    '"red_flag_alerts" (each a JSON array of strings, with no duplicate '
    'entries within the same array), "clinical_reasoning" (a narrative '
    "explanation grounding every risk score and recommendation you made "
    "in the vital signs, laboratory values, and clinical context given "
    'to you), and "confidence_score" (a number between 0.0 and 1.0). '
    "Only report risk factors or scores clearly supported by the "
    "vital signs, laboratory values, history, or clinical context given "
    "to you — never invent a finding that was not provided or reasonably "
    "inferable from it. Do not include placeholder text such as "
    '"[insert]", "TBD", "XXX", or "Lorem ipsum" anywhere in your '
    "response."
)

_USER_TEMPLATE = (
    "Patient risk stratification request:\n\n"
    "Patient Age: {{ patient_age }}\n"
    "Vital Signs: {{ vital_signs }}\n"
    "Laboratory Values: {{ lab_values }}\n\n"
    "Medical History: {{ medical_history }}\n"
    "Diagnoses: {{ diagnoses }}\n"
    "Current Medications: {{ current_medications }}\n"
    "Allergies: {{ allergies }}\n"
    "Clinical Notes: {{ clinical_notes }}\n"
    "SOAP Notes: {{ soap_notes }}\n\n"
    "Laboratory Interpretation: {{ laboratory_interpretation }}\n"
    "Radiology Interpretation: {{ radiology_interpretation }}\n"
    "Pathology Interpretation: {{ pathology_interpretation }}\n"
    "Medical Reasoning Context: {{ medical_reasoning_context }}\n\n"
    "Produce a structured risk stratification and early warning "
    "assessment now."
)

_USER_TEMPLATE_VARIABLES = frozenset(
    {
        "patient_age",
        "vital_signs",
        "lab_values",
        "medical_history",
        "diagnoses",
        "current_medications",
        "allergies",
        "clinical_notes",
        "soap_notes",
        "laboratory_interpretation",
        "radiology_interpretation",
        "pathology_interpretation",
        "medical_reasoning_context",
    }
)

_SYSTEM_TEMPLATE_VARIABLES = frozenset({"language"})

_STYLE_GUIDANCE: dict[RiskStratificationSetting, str] = {
    RiskStratificationSetting.EMERGENCY: (
        "You are an expert clinical risk stratification engine producing "
        "structured decision-support in {{ language }}, appropriate for "
        "an emergency department encounter — prioritize identifying "
        "time-critical deterioration risk (sepsis, respiratory failure, "
        "cardiovascular collapse) above all else."
    ),
    RiskStratificationSetting.INPATIENT: (
        "You are an expert clinical risk stratification engine producing "
        "structured decision-support in {{ language }}, appropriate for "
        "an inpatient admission — weigh trends across the admission and "
        "highlight anything that would change the level of monitoring or "
        "care."
    ),
    RiskStratificationSetting.ICU: (
        "You are an expert clinical risk stratification engine producing "
        "structured decision-support in {{ language }}, appropriate for "
        "a critically ill ICU patient — weigh organ-support therapies, "
        "hemodynamic instability, and rapidly changing vital signs "
        "carefully."
    ),
    RiskStratificationSetting.OUTPATIENT: (
        "You are an expert clinical risk stratification engine producing "
        "structured decision-support in {{ language }}, appropriate for "
        "a routine outpatient encounter. Ground every finding in the "
        "vital signs and context given to you."
    ),
    RiskStratificationSetting.PEDIATRIC: (
        "You are an expert clinical risk stratification engine producing "
        "structured decision-support in {{ language }}, appropriate for "
        "a pediatric patient — consider age-appropriate vital sign norms "
        "and explicitly flag deterioration patterns that present "
        "differently in children."
    ),
    RiskStratificationSetting.GERIATRIC: (
        "You are an expert clinical risk stratification engine producing "
        "structured decision-support in {{ language }}, appropriate for "
        "a geriatric patient — consider atypical presentations, "
        "polypharmacy, fall risk, and frailty carefully."
    ),
}


def system_template_name(risk_setting: RiskStratificationSetting) -> str:
    return f"risk_stratification.{risk_setting.value}.system"


def developer_template_name(risk_setting: RiskStratificationSetting) -> str:
    return f"risk_stratification.{risk_setting.value}.developer"


def user_template_name(risk_setting: RiskStratificationSetting) -> str:
    return f"risk_stratification.{risk_setting.value}.user"


def build_all_templates(*, version: int = 1) -> list[PromptTemplate]:
    """Constructs the full 18-template set (6 settings x system/
    developer/user) at the given version — called once by
    `template_registrar.py`."""
    templates: list[PromptTemplate] = []
    for risk_setting, guidance in _STYLE_GUIDANCE.items():
        templates.append(
            PromptTemplate(
                name=system_template_name(risk_setting),
                version=version,
                template_string=guidance,
                variable_names=_SYSTEM_TEMPLATE_VARIABLES,
                description=f"System prompt for {risk_setting.value} risk stratification.",
            )
        )
        templates.append(
            PromptTemplate(
                name=developer_template_name(risk_setting),
                version=version,
                template_string=_JSON_CONTRACT,
                variable_names=frozenset(),
                description=f"JSON output contract for {risk_setting.value} risk stratification.",
            )
        )
        templates.append(
            PromptTemplate(
                name=user_template_name(risk_setting),
                version=version,
                template_string=_USER_TEMPLATE,
                variable_names=_USER_TEMPLATE_VARIABLES,
                description=(
                    f"Clinical context prompt for {risk_setting.value} risk stratification."
                ),
            )
        )
    return templates

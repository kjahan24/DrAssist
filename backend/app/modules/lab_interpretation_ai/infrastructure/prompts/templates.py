"""Production prompt templates for the AI Lab Interpretation module — one
`(system, developer, user)` triple per `LabInterpretationSetting`, each
independently versioned, registered into AI Foundation's shared
`PromptRegistry` by `template_registrar.py`.

Imports AI Foundation's `domain.value_objects.PromptTemplate` directly
(not `.public`) — the same justified exception every prior AI module's
own `infrastructure/prompts/templates.py` module docstring documents in
full: constructing instances of it to register is exactly the mechanism
`app.modules.ai.container.get_prompt_registry`'s own docstring anticipates
and names for this purpose; nothing in AI Foundation's own source is
modified.

Template names are prefixed `lab_interpretation` — deliberately distinct
from the pre-existing, persisted sibling modules `app.modules.lab_orders`
and `app.modules.lab_results` (neither of which registers AI Foundation
prompt templates at all, but the prefix is still chosen to avoid any
reader confusion between "AI interpretation of lab results" and either
of those two modules' own, unrelated concerns), the same
sibling-disambiguation precedent `app.modules.icd10_ai`/
`app.modules.prescription_ai`/`app.modules.differential_diagnosis_ai`
each establish for their own persisted-sibling situation.

Every `developer` template carries the same fixed JSON-output contract —
`overall_interpretation`, `findings` (an array of `{test_name, value,
numeric_value, unit, flag}` objects — this task's "Abnormal Findings"/
"Critical Values" OUTPUT fields are computed views over this one array,
filtered by `flag`, per `LabInterpretationResult`'s own docstring),
`clinical_significance`, `supporting_evidence`, `potential_causes`,
`suggested_follow_up_tests`, `monitoring_recommendations`,
`red_flag_warnings`, and `confidence_score` — matching this task's own
OUTPUT specification field-for-field. `system` templates carry
setting-specific tone/priority guidance; `user` templates are the lab
data/clinical-context placeholders `infrastructure/prompts
/prompt_builder.py` fills in.
"""

from app.modules.ai.domain.value_objects import PromptTemplate
from app.modules.lab_interpretation_ai.domain.enums import LabInterpretationSetting

_JSON_CONTRACT = (
    "You must respond with ONLY a single JSON object and nothing else — "
    "no markdown code fences, no prose before or after it. This is "
    "clinical decision-support laboratory interpretation only — you "
    "never provide a definitive diagnosis and never replace physician "
    "judgment. The JSON object must have exactly these nine keys:\n\n"
    '"overall_interpretation" (a concise narrative summary of the '
    'laboratory picture as a whole), "findings" (a JSON array of '
    'objects, one per lab value you were given, each with "test_name", '
    '"value" (the result as reported), "numeric_value" (a number, or '
    'null if the result is not numeric), "unit" (a string, or null), '
    'and "flag" — exactly one of "normal", "abnormal_low", '
    '"abnormal_high", "critical_low", or "critical_high"), '
    '"clinical_significance" (a narrative explanation of what the '
    "abnormal or critical findings may mean clinically), "
    '"supporting_evidence" (a JSON array of strings grounding your '
    'interpretation in the specific values given), "potential_causes" '
    "(a JSON array of strings — possible, non-definitive explanations "
    'for the abnormal findings), "suggested_follow_up_tests" and '
    '"monitoring_recommendations" (each a JSON array of strings, with '
    'no duplicate entries within the same array), "red_flag_warnings" '
    "(a JSON array of strings naming any finding that may require "
    "urgent clinical attention — an empty array when none apply), and "
    '"confidence_score" (a number between 0.0 and 1.0). Only report '
    "findings, causes, or recommendations clearly supported by the "
    "laboratory values and clinical context given to you — never "
    "invent a value that was not provided. Do not include placeholder "
    'text such as "[insert]", "TBD", "XXX", or "Lorem ipsum" anywhere '
    "in your response."
)

_USER_TEMPLATE = (
    "Laboratory values for interpretation:\n\n"
    "Lab Values: {{ lab_values }}\n\n"
    "Patient Age: {{ patient_age }}\n"
    "Patient Sex: {{ patient_sex }}\n"
    "Pregnancy Status: {{ pregnancy_status }}\n"
    "Visit Type: {{ visit_type }}\n"
    "Medical Conditions: {{ medical_conditions }}\n"
    "Allergies: {{ allergies }}\n"
    "Medications: {{ medications }}\n"
    "Clinical Notes: {{ clinical_notes }}\n"
    "SOAP Notes: {{ soap_notes }}\n\n"
    "Produce a structured laboratory interpretation now."
)

_USER_TEMPLATE_VARIABLES = frozenset(
    {
        "lab_values",
        "patient_age",
        "patient_sex",
        "pregnancy_status",
        "visit_type",
        "medical_conditions",
        "allergies",
        "medications",
        "clinical_notes",
        "soap_notes",
    }
)

_SYSTEM_TEMPLATE_VARIABLES = frozenset({"language"})

_STYLE_GUIDANCE: dict[LabInterpretationSetting, str] = {
    LabInterpretationSetting.OUTPATIENT: (
        "You are an expert laboratory interpretation engine producing "
        "structured clinical decision-support in {{ language }}, "
        "appropriate for a routine outpatient encounter. Ground every "
        "conclusion in the values given to you."
    ),
    LabInterpretationSetting.INPATIENT: (
        "You are an expert laboratory interpretation engine producing "
        "structured clinical decision-support in {{ language }}, "
        "appropriate for an inpatient admission — weigh the evolving "
        "clinical picture and highlight anything that would change "
        "inpatient management or monitoring frequency."
    ),
    LabInterpretationSetting.EMERGENCY: (
        "You are an expert laboratory interpretation engine producing "
        "structured clinical decision-support in {{ language }}, "
        "appropriate for an emergency department encounter — prioritize "
        "identifying critical, life-threatening laboratory values and "
        "their red-flag warnings above all else."
    ),
    LabInterpretationSetting.PEDIATRIC: (
        "You are an expert laboratory interpretation engine producing "
        "structured clinical decision-support in {{ language }}, "
        "appropriate for a pediatric patient — consider age-specific "
        "reference ranges and explicitly flag findings that are more "
        "urgent or present differently in children."
    ),
    LabInterpretationSetting.GERIATRIC: (
        "You are an expert laboratory interpretation engine producing "
        "structured clinical decision-support in {{ language }}, "
        "appropriate for a geriatric patient — consider age-related "
        "reference range shifts, polypharmacy-related contributors, and "
        "comorbidity-driven risk."
    ),
}


def system_template_name(lab_setting: LabInterpretationSetting) -> str:
    return f"lab_interpretation.{lab_setting.value}.system"


def developer_template_name(lab_setting: LabInterpretationSetting) -> str:
    return f"lab_interpretation.{lab_setting.value}.developer"


def user_template_name(lab_setting: LabInterpretationSetting) -> str:
    return f"lab_interpretation.{lab_setting.value}.user"


def build_all_templates(*, version: int = 1) -> list[PromptTemplate]:
    """Constructs the full 15-template set (5 settings x system/
    developer/user) at the given version — called once by
    `template_registrar.py`."""
    templates: list[PromptTemplate] = []
    for lab_setting, guidance in _STYLE_GUIDANCE.items():
        templates.append(
            PromptTemplate(
                name=system_template_name(lab_setting),
                version=version,
                template_string=guidance,
                variable_names=_SYSTEM_TEMPLATE_VARIABLES,
                description=f"System prompt for {lab_setting.value} lab interpretation.",
            )
        )
        templates.append(
            PromptTemplate(
                name=developer_template_name(lab_setting),
                version=version,
                template_string=_JSON_CONTRACT,
                variable_names=frozenset(),
                description=f"JSON output contract for {lab_setting.value} lab interpretation.",
            )
        )
        templates.append(
            PromptTemplate(
                name=user_template_name(lab_setting),
                version=version,
                template_string=_USER_TEMPLATE,
                variable_names=_USER_TEMPLATE_VARIABLES,
                description=f"Laboratory data prompt for {lab_setting.value} lab interpretation.",
            )
        )
    return templates

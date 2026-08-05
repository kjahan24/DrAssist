"""Production prompt templates for the AI Radiology Interpretation
module — one `(system, developer, user)` triple per `RadiologySetting`,
each independently versioned, registered into AI Foundation's shared
`PromptRegistry` by `template_registrar.py`.

Imports AI Foundation's `domain.value_objects.PromptTemplate` directly
(not `.public`) — the same justified exception every prior AI module's
own `infrastructure/prompts/templates.py` module docstring documents in
full: constructing instances of it to register is exactly the mechanism
`app.modules.ai.container.get_prompt_registry`'s own docstring anticipates
and names for this purpose; nothing in AI Foundation's own source is
modified.

Template names are prefixed `radiology_interpretation` — no pre-existing,
persisted sibling module shares this name (unlike
`app.modules.lab_interpretation_ai`, which had to disambiguate against
`app.modules.lab_orders`/`app.modules.lab_results`), so no further
disambiguation is needed.

Every `developer` template carries the same fixed JSON-output contract —
`examination_summary`, `findings` (an array of `{description, category,
anatomical_region}` objects — this task's "Important Findings"/"Normal
Findings"/"Abnormal Findings"/"Incidental Findings"/"Critical Findings"
OUTPUT fields are computed views over this one array, filtered by
`category`, per `RadiologyInterpretationResult`'s own docstring),
`clinical_significance`, `differential_imaging_considerations`,
`suggested_follow_up_imaging`, `suggested_specialist_referral`,
`red_flag_warnings`, `confidence_score`, and `clinical_reasoning` —
matching this task's own OUTPUT specification field-for-field. `system`
templates carry setting-specific tone/priority guidance; `user` templates
are the report-text/clinical-context placeholders `infrastructure/prompts
/prompt_builder.py` fills in. This module interprets **textual radiology
reports only** — every template is explicit that raw DICOM imaging is
never provided or expected, and that the output is clinical
decision-support, never a replacement for radiologist review, per this
task's own GOAL section.
"""

from app.modules.ai.domain.value_objects import PromptTemplate
from app.modules.radiology_interpretation_ai.domain.enums import RadiologySetting

_JSON_CONTRACT = (
    "You must respond with ONLY a single JSON object and nothing else — "
    "no markdown code fences, no prose before or after it. You interpret "
    "TEXTUAL radiology reports only — you never receive or interpret raw "
    "DICOM images, and you never replace radiologist review or provide a "
    "definitive diagnosis; this is clinical decision-support only. The "
    "JSON object must have exactly these nine keys:\n\n"
    '"examination_summary" (a concise narrative summary of the '
    'examination and its overall impression), "findings" (a JSON array '
    "of objects, one per distinct finding in the report, each with "
    '"description", "category" — exactly one of "normal", "abnormal", '
    '"incidental", or "critical" — and "anatomical_region" (a string, or '
    'null when not applicable)), "clinical_significance" (a narrative '
    "explanation of what the abnormal, incidental, or critical findings "
    'may mean clinically), "differential_imaging_considerations" (a '
    "JSON array of strings — possible, non-definitive imaging "
    "differentials suggested by the findings), "
    '"suggested_follow_up_imaging" and "suggested_specialist_referral" '
    "(each a JSON array of strings, with no duplicate entries within the "
    'same array), "red_flag_warnings" (a JSON array of strings naming '
    "any finding that may require urgent clinical attention — an empty "
    'array when none apply), "confidence_score" (a number between 0.0 '
    'and 1.0), and "clinical_reasoning" (a narrative explanation '
    "grounding every finding and recommendation you made in the report "
    "text given to you). Only report findings, considerations, or "
    "recommendations clearly supported by the report text and clinical "
    "context given to you — never invent a finding that was not "
    "provided or reasonably inferable from it. Do not include "
    'placeholder text such as "[insert]", "TBD", "XXX", or "Lorem '
    'ipsum" anywhere in your response.'
)

_USER_TEMPLATE = (
    "Radiology report for interpretation:\n\n"
    "Examination Type: {{ examination_type }}\n"
    "Report Text: {{ report_text }}\n\n"
    "Patient Age: {{ patient_age }}\n"
    "Patient Sex: {{ patient_sex }}\n"
    "Pregnancy Status: {{ pregnancy_status }}\n"
    "Visit Type: {{ visit_type }}\n"
    "Clinical Notes: {{ clinical_notes }}\n"
    "SOAP Notes: {{ soap_notes }}\n"
    "ICD-10 Suggestions: {{ icd10_suggestions }}\n"
    "Differential Diagnoses: {{ differential_diagnoses }}\n"
    "Laboratory Interpretation: {{ laboratory_interpretation }}\n"
    "Medical Reasoning Context: {{ medical_reasoning_context }}\n\n"
    "Produce a structured radiology interpretation now."
)

_USER_TEMPLATE_VARIABLES = frozenset(
    {
        "examination_type",
        "report_text",
        "patient_age",
        "patient_sex",
        "pregnancy_status",
        "visit_type",
        "clinical_notes",
        "soap_notes",
        "icd10_suggestions",
        "differential_diagnoses",
        "laboratory_interpretation",
        "medical_reasoning_context",
    }
)

_SYSTEM_TEMPLATE_VARIABLES = frozenset({"language"})

_STYLE_GUIDANCE: dict[RadiologySetting, str] = {
    RadiologySetting.OUTPATIENT: (
        "You are an expert radiology report interpretation engine "
        "producing structured clinical decision-support in "
        "{{ language }}, appropriate for a routine outpatient encounter. "
        "Ground every finding in the report text given to you."
    ),
    RadiologySetting.INPATIENT: (
        "You are an expert radiology report interpretation engine "
        "producing structured clinical decision-support in "
        "{{ language }}, appropriate for an inpatient admission — weigh "
        "the evolving clinical picture and highlight anything that would "
        "change inpatient management or monitoring."
    ),
    RadiologySetting.EMERGENCY: (
        "You are an expert radiology report interpretation engine "
        "producing structured clinical decision-support in "
        "{{ language }}, appropriate for an emergency department "
        "encounter — prioritize identifying critical, life-threatening "
        "imaging findings and their red-flag warnings above all else."
    ),
    RadiologySetting.PEDIATRIC: (
        "You are an expert radiology report interpretation engine "
        "producing structured clinical decision-support in "
        "{{ language }}, appropriate for a pediatric patient — consider "
        "age-specific presentations and explicitly flag findings that "
        "are more urgent or present differently in children."
    ),
    RadiologySetting.GERIATRIC: (
        "You are an expert radiology report interpretation engine "
        "producing structured clinical decision-support in "
        "{{ language }}, appropriate for a geriatric patient — consider "
        "age-related findings, incidental findings common in older "
        "adults, and comorbidity-driven risk."
    ),
}


def system_template_name(radiology_setting: RadiologySetting) -> str:
    return f"radiology_interpretation.{radiology_setting.value}.system"


def developer_template_name(radiology_setting: RadiologySetting) -> str:
    return f"radiology_interpretation.{radiology_setting.value}.developer"


def user_template_name(radiology_setting: RadiologySetting) -> str:
    return f"radiology_interpretation.{radiology_setting.value}.user"


def build_all_templates(*, version: int = 1) -> list[PromptTemplate]:
    """Constructs the full 15-template set (5 settings x system/
    developer/user) at the given version — called once by
    `template_registrar.py`."""
    templates: list[PromptTemplate] = []
    for radiology_setting, guidance in _STYLE_GUIDANCE.items():
        templates.append(
            PromptTemplate(
                name=system_template_name(radiology_setting),
                version=version,
                template_string=guidance,
                variable_names=_SYSTEM_TEMPLATE_VARIABLES,
                description=(
                    f"System prompt for {radiology_setting.value} radiology interpretation."
                ),
            )
        )
        templates.append(
            PromptTemplate(
                name=developer_template_name(radiology_setting),
                version=version,
                template_string=_JSON_CONTRACT,
                variable_names=frozenset(),
                description=(
                    f"JSON output contract for {radiology_setting.value} radiology "
                    "interpretation."
                ),
            )
        )
        templates.append(
            PromptTemplate(
                name=user_template_name(radiology_setting),
                version=version,
                template_string=_USER_TEMPLATE,
                variable_names=_USER_TEMPLATE_VARIABLES,
                description=(
                    f"Radiology report prompt for {radiology_setting.value} radiology "
                    "interpretation."
                ),
            )
        )
    return templates

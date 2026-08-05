"""Production prompt templates for the AI Pathology Interpretation
module — one `(system, developer, user)` triple per `PathologySetting`,
each independently versioned, registered into AI Foundation's shared
`PromptRegistry` by `template_registrar.py`.

Imports AI Foundation's `domain.value_objects.PromptTemplate` directly
(not `.public`) — the same justified exception every prior AI module's
own `infrastructure/prompts/templates.py` module docstring documents in
full: constructing instances of it to register is exactly the mechanism
`app.modules.ai.container.get_prompt_registry`'s own docstring anticipates
and names for this purpose; nothing in AI Foundation's own source is
modified.

Template names are prefixed `pathology_interpretation` — no pre-existing,
persisted sibling module shares this name, so no further disambiguation
is needed, the same situation
`app.modules.radiology_interpretation_ai.infrastructure.prompts.templates`
documents for itself.

Every `developer` template carries the same fixed JSON-output contract —
`pathology_summary`, `key_findings`, `microscopic_findings` (an array of
`{description, category, anatomical_site}` objects — this task's "Benign
Features"/"Malignant Features"/"Atypical Findings" OUTPUT fields are
computed views over this one array, filtered by `category`, per
`PathologyInterpretationResult`'s own docstring), `final_impression`,
`clinical_significance`, `correlation_recommendations`,
`suggested_follow_up`, `suggested_specialist_referral`,
`red_flag_warnings`, `confidence_score`, and `clinical_reasoning` —
matching this task's own OUTPUT specification field-for-field. `system`
templates carry setting-specific tone/priority guidance across this
task's own five settings (outpatient/inpatient/emergency/oncology/
pediatric — note "oncology," not "geriatric," per this task's own
PROMPTS section); `user` templates are the report-text/clinical-context
placeholders `infrastructure/prompts/prompt_builder.py` fills in. This
module interprets **textual pathology reports only** — every template is
explicit that microscope/whole-slide imaging is never provided or
expected, and that the output is clinical decision-support, never a
replacement for pathologist review, per this task's own GOAL section.
"""

from app.modules.ai.domain.value_objects import PromptTemplate
from app.modules.pathology_interpretation_ai.domain.enums import PathologySetting

_JSON_CONTRACT = (
    "You must respond with ONLY a single JSON object and nothing else — "
    "no markdown code fences, no prose before or after it. You interpret "
    "TEXTUAL pathology reports only — you never receive or interpret "
    "microscope images or whole-slide images, and you never replace "
    "pathologist review or provide a definitive diagnosis; this is "
    "clinical decision-support only. The JSON object must have exactly "
    "these eleven keys:\n\n"
    '"pathology_summary" (a concise narrative summary of the specimen '
    'and its overall findings), "key_findings" (a JSON array of strings '
    "highlighting the most clinically important points of the report), "
    '"microscopic_findings" (a JSON array of objects, one per distinct '
    'microscopic finding, each with "description", "category" — exactly '
    'one of "benign", "malignant", or "atypical" — and "anatomical_site" '
    '(a string, or null when not applicable)), "final_impression" (the '
    'overall diagnostic impression), "clinical_significance" (a '
    "narrative explanation of what the malignant or atypical findings "
    'may mean clinically), "correlation_recommendations", '
    '"suggested_follow_up", and "suggested_specialist_referral" (each a '
    "JSON array of strings, with no duplicate entries within the same "
    'array), "red_flag_warnings" (a JSON array of strings naming any '
    "finding that may require urgent clinical attention — an empty "
    'array when none apply), "confidence_score" (a number between 0.0 '
    'and 1.0), and "clinical_reasoning" (a narrative explanation '
    "grounding every finding and recommendation you made in the report "
    "text given to you). Only report findings, correlations, or "
    "recommendations clearly supported by the report text and clinical "
    "context given to you — never invent a finding that was not "
    "provided or reasonably inferable from it. Do not include "
    'placeholder text such as "[insert]", "TBD", "XXX", or "Lorem '
    'ipsum" anywhere in your response.'
)

_USER_TEMPLATE = (
    "Pathology report for interpretation:\n\n"
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
    "Radiology Interpretation: {{ radiology_interpretation }}\n"
    "Medical Reasoning Context: {{ medical_reasoning_context }}\n\n"
    "Produce a structured pathology interpretation now."
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
        "radiology_interpretation",
        "medical_reasoning_context",
    }
)

_SYSTEM_TEMPLATE_VARIABLES = frozenset({"language"})

_STYLE_GUIDANCE: dict[PathologySetting, str] = {
    PathologySetting.OUTPATIENT: (
        "You are an expert pathology report interpretation engine "
        "producing structured clinical decision-support in "
        "{{ language }}, appropriate for a routine outpatient encounter. "
        "Ground every finding in the report text given to you."
    ),
    PathologySetting.INPATIENT: (
        "You are an expert pathology report interpretation engine "
        "producing structured clinical decision-support in "
        "{{ language }}, appropriate for an inpatient admission — weigh "
        "the evolving clinical picture and highlight anything that would "
        "change inpatient management or monitoring."
    ),
    PathologySetting.EMERGENCY: (
        "You are an expert pathology report interpretation engine "
        "producing structured clinical decision-support in "
        "{{ language }}, appropriate for an emergency or urgent-care "
        "encounter — prioritize identifying malignant or otherwise "
        "critical findings and their red-flag warnings above all else."
    ),
    PathologySetting.ONCOLOGY: (
        "You are an expert pathology report interpretation engine "
        "producing structured clinical decision-support in "
        "{{ language }}, appropriate for an oncology encounter — weigh "
        "malignancy grading, margins, and ancillary-study correlation "
        "carefully, and highlight anything that would change oncologic "
        "management or staging."
    ),
    PathologySetting.PEDIATRIC: (
        "You are an expert pathology report interpretation engine "
        "producing structured clinical decision-support in "
        "{{ language }}, appropriate for a pediatric patient — consider "
        "age-specific presentations and explicitly flag findings that "
        "are more urgent or present differently in children."
    ),
}


def system_template_name(pathology_setting: PathologySetting) -> str:
    return f"pathology_interpretation.{pathology_setting.value}.system"


def developer_template_name(pathology_setting: PathologySetting) -> str:
    return f"pathology_interpretation.{pathology_setting.value}.developer"


def user_template_name(pathology_setting: PathologySetting) -> str:
    return f"pathology_interpretation.{pathology_setting.value}.user"


def build_all_templates(*, version: int = 1) -> list[PromptTemplate]:
    """Constructs the full 15-template set (5 settings x system/
    developer/user) at the given version — called once by
    `template_registrar.py`."""
    templates: list[PromptTemplate] = []
    for pathology_setting, guidance in _STYLE_GUIDANCE.items():
        templates.append(
            PromptTemplate(
                name=system_template_name(pathology_setting),
                version=version,
                template_string=guidance,
                variable_names=_SYSTEM_TEMPLATE_VARIABLES,
                description=(
                    f"System prompt for {pathology_setting.value} pathology interpretation."
                ),
            )
        )
        templates.append(
            PromptTemplate(
                name=developer_template_name(pathology_setting),
                version=version,
                template_string=_JSON_CONTRACT,
                variable_names=frozenset(),
                description=(
                    f"JSON output contract for {pathology_setting.value} pathology "
                    "interpretation."
                ),
            )
        )
        templates.append(
            PromptTemplate(
                name=user_template_name(pathology_setting),
                version=version,
                template_string=_USER_TEMPLATE,
                variable_names=_USER_TEMPLATE_VARIABLES,
                description=(
                    f"Pathology report prompt for {pathology_setting.value} pathology "
                    "interpretation."
                ),
            )
        )
    return templates

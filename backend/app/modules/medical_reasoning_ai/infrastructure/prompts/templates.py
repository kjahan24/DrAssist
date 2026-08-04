"""Production prompt templates for the AI Medical Reasoning Engine — one
`(system, developer, user)` triple per `ReasoningSetting`, each
independently versioned, registered into AI Foundation's shared
`PromptRegistry` by `template_registrar.py`.

Imports AI Foundation's `domain.value_objects.PromptTemplate` directly
(not `.public`) — the same justified exception
`app.modules.differential_diagnosis_ai.infrastructure.prompts.templates`'s
own module docstring documents in full: constructing instances of it to
register is exactly the mechanism `app.modules.ai.container
.get_prompt_registry`'s own docstring anticipates and names for this
purpose; nothing in AI Foundation's own source is modified.

Template names are prefixed `medical_reasoning` — unlike
`app.modules.icd10_ai`/`app.modules.prescription_ai`/
`app.modules.differential_diagnosis_ai`, there is no pre-existing,
persisted sibling module sharing this name to disambiguate against
(no `app.modules.medical_reasoning` exists), so the shorter prefix is
unambiguous.

Every `developer` template carries the same fixed JSON-output contract —
`clinical_summary`, `evidence` (an array of `{description, weight,
polarity}` objects), `missing_information`, three confidence numbers,
`risk_factors`, `red_flags` (an array of `{description, priority}`
objects), the three recommendation arrays, and `clinical_justification` —
matching this task's own OUTPUT specification field-for-field. `system`
templates carry setting-specific tone/priority guidance; `user` templates
are the clinical-evidence placeholders `infrastructure/prompts
/prompt_builder.py` fills in.
"""

from app.modules.ai.domain.value_objects import PromptTemplate
from app.modules.medical_reasoning_ai.domain.enums import ReasoningSetting

_JSON_CONTRACT = (
    "You must respond with ONLY a single JSON object and nothing else — "
    "no markdown code fences, no prose before or after it. This is "
    "clinical decision-support reasoning only — you never issue a final "
    "diagnosis, prescription, or treatment plan, and you never replace "
    "physician judgment. The JSON object must have exactly these twelve "
    'keys:\n\n"clinical_summary" (a concise narrative summary of the '
    'clinical picture), "evidence" (a JSON array of objects, each with '
    '"description", "weight" (a number between 0.0 and 1.0), and '
    '"polarity" (exactly "supporting" or "contradicting") — never repeat '
    "the exact same description text for two different evidence items), "
    '"missing_information" (a JSON array of strings describing clinically '
    'relevant information that was not provided), "clinical_confidence", '
    '"diagnostic_confidence", and "therapeutic_confidence" (each a number '
    'between 0.0 and 1.0), "risk_factors" (a JSON array of strings), '
    '"red_flags" (a JSON array of objects, each with "description" and '
    '"priority" — exactly "low", "moderate", "high", or "critical"), '
    '"suggested_next_questions", "suggested_investigations", and '
    '"suggested_monitoring" (each a JSON array of strings, with no '
    'duplicate entries within the same array), and "clinical_justification" '
    "(a narrative explanation grounding every recommendation you made in "
    "the evidence above). Only report evidence, risks, or recommendations "
    "clearly supported by the clinical information given to you — never "
    "invent a finding that was not provided or reasonably inferable from "
    'it. Do not include placeholder text such as "[insert]", "TBD", '
    '"XXX", or "Lorem ipsum" anywhere in your response.'
)

_USER_TEMPLATE = (
    "Clinical evidence for medical reasoning:\n\n"
    "Patient Age: {{ patient_age }}\n"
    "Patient Sex: {{ patient_sex }}\n"
    "Pregnancy Status: {{ pregnancy_status }}\n"
    "Visit Type: {{ visit_type }}\n"
    "Chief Complaint: {{ chief_complaint }}\n"
    "History of Present Illness: {{ history_of_present_illness }}\n"
    "Symptoms: {{ symptoms }}\n"
    "Review of Systems: {{ review_of_systems }}\n"
    "Physical Examination: {{ physical_examination }}\n"
    "Vitals: {{ vitals }}\n"
    "Allergies: {{ allergies }}\n"
    "Medications: {{ medications }}\n"
    "Medical Conditions: {{ medical_conditions }}\n"
    "Laboratory Results: {{ laboratory_results }}\n"
    "Imaging Summary: {{ imaging_summary }}\n"
    "Clinical Notes: {{ clinical_notes }}\n"
    "SOAP Notes: {{ soap_notes }}\n"
    "Diagnoses: {{ diagnoses }}\n"
    "ICD-10 Suggestions: {{ icd10_suggestions }}\n"
    "Prescription Suggestions: {{ prescription_suggestions }}\n"
    "Differential Diagnoses: {{ differential_diagnoses }}\n\n"
    "Produce structured clinical reasoning now."
)

_USER_TEMPLATE_VARIABLES = frozenset(
    {
        "patient_age",
        "patient_sex",
        "pregnancy_status",
        "visit_type",
        "chief_complaint",
        "history_of_present_illness",
        "symptoms",
        "review_of_systems",
        "physical_examination",
        "vitals",
        "allergies",
        "medications",
        "medical_conditions",
        "laboratory_results",
        "imaging_summary",
        "clinical_notes",
        "soap_notes",
        "diagnoses",
        "icd10_suggestions",
        "prescription_suggestions",
        "differential_diagnoses",
    }
)

_SYSTEM_TEMPLATE_VARIABLES = frozenset({"language"})

_STYLE_GUIDANCE: dict[ReasoningSetting, str] = {
    ReasoningSetting.OUTPATIENT: (
        "You are an expert clinical reasoning engine producing structured "
        "decision-support reasoning in {{ language }}, appropriate for a "
        "routine outpatient encounter. Ground every conclusion in the "
        "evidence given to you and be explicit about what information is "
        "missing."
    ),
    ReasoningSetting.INPATIENT: (
        "You are an expert clinical reasoning engine producing structured "
        "decision-support reasoning in {{ language }}, appropriate for an "
        "inpatient admission — weigh the evolving clinical picture and "
        "comorbidities across the stay, and highlight anything that would "
        "change inpatient management."
    ),
    ReasoningSetting.EMERGENCY: (
        "You are an expert clinical reasoning engine producing structured "
        "decision-support reasoning in {{ language }}, appropriate for an "
        "emergency department encounter — prioritize identifying acute, "
        "life-threatening, or time-sensitive concerns and their red-flag "
        "indicators above all else."
    ),
    ReasoningSetting.PEDIATRIC: (
        "You are an expert clinical reasoning engine producing structured "
        "decision-support reasoning in {{ language }}, appropriate for a "
        "pediatric patient — consider age-specific presentations and "
        "explicitly flag findings that are more urgent or present "
        "differently in children."
    ),
    ReasoningSetting.GERIATRIC: (
        "You are an expert clinical reasoning engine producing structured "
        "decision-support reasoning in {{ language }}, appropriate for a "
        "geriatric patient — consider atypical presentations common in "
        "older adults, polypharmacy-related contributors, and "
        "comorbidity-driven risk."
    ),
}


def system_template_name(reasoning_setting: ReasoningSetting) -> str:
    return f"medical_reasoning.{reasoning_setting.value}.system"


def developer_template_name(reasoning_setting: ReasoningSetting) -> str:
    return f"medical_reasoning.{reasoning_setting.value}.developer"


def user_template_name(reasoning_setting: ReasoningSetting) -> str:
    return f"medical_reasoning.{reasoning_setting.value}.user"


def build_all_templates(*, version: int = 1) -> list[PromptTemplate]:
    """Constructs the full 15-template set (5 settings x system/
    developer/user) at the given version — called once by
    `template_registrar.py`."""
    templates: list[PromptTemplate] = []
    for reasoning_setting, guidance in _STYLE_GUIDANCE.items():
        templates.append(
            PromptTemplate(
                name=system_template_name(reasoning_setting),
                version=version,
                template_string=guidance,
                variable_names=_SYSTEM_TEMPLATE_VARIABLES,
                description=f"System prompt for {reasoning_setting.value} medical reasoning.",
            )
        )
        templates.append(
            PromptTemplate(
                name=developer_template_name(reasoning_setting),
                version=version,
                template_string=_JSON_CONTRACT,
                variable_names=frozenset(),
                description=(
                    f"JSON output contract for {reasoning_setting.value} medical reasoning."
                ),
            )
        )
        templates.append(
            PromptTemplate(
                name=user_template_name(reasoning_setting),
                version=version,
                template_string=_USER_TEMPLATE,
                variable_names=_USER_TEMPLATE_VARIABLES,
                description=(
                    f"Clinical evidence prompt for {reasoning_setting.value} medical reasoning."
                ),
            )
        )
    return templates

"""Production prompt templates for AI Differential Diagnosis — one
`(system, developer, user)` triple per `ClinicalSetting`, each
independently versioned, registered into AI Foundation's shared
`PromptRegistry` by `template_registrar.py`.

Imports AI Foundation's `domain.value_objects.PromptTemplate` directly
(not `.public`) — the same justified exception
`app.modules.prescription_ai.infrastructure.prompts.templates`'s own
module docstring documents in full: constructing instances of it to
register is exactly the mechanism `app.modules.ai.container
.get_prompt_registry`'s own docstring anticipates and names for this
purpose; nothing in AI Foundation's own source is modified.

Template names are prefixed `differential_diagnosis_suggestion`, not
`differential_diagnosis_ai` or `differential_diagnosis` — the former
would just restate this module's own name, and the latter is
deliberately avoided to prevent any reader confusing an AI-Foundation
`PromptRegistry` entry (a process-lifetime, in-memory string key, scoped
only within AI Foundation) with the pre-existing, persisted
`app.modules.differential_diagnosis` module (an unrelated, completed
module this task does not touch) — the same precedent
`app.modules.icd10_ai.infrastructure.prompts.templates` and
`app.modules.prescription_ai.infrastructure.prompts.templates` each
establish relative to their own persisted sibling modules.

Every `developer` template carries the same fixed JSON-output contract:
a `"candidates"` array (nine keys per this task's own OUTPUT
specification), plus `"serious_diagnoses_not_to_miss"`,
`"suggested_investigations"`, and `"suggested_referrals"` string arrays.
`system` templates carry setting-specific tone/priority guidance; `user`
templates are the clinical-evidence placeholders `infrastructure/prompts
/prompt_builder.py` fills in.
"""

from app.modules.ai.domain.value_objects import PromptTemplate
from app.modules.differential_diagnosis_ai.domain.enums import ClinicalSetting

_JSON_CONTRACT = (
    "You must respond with ONLY a single JSON object and nothing else — "
    "no markdown code fences, no prose before or after it. This is "
    "clinical decision-support only — you are never creating a final "
    "diagnosis and never replacing physician judgment. The JSON object "
    "must have exactly these four keys:\n\n"
    '1. "candidates": a JSON array of zero or more differential '
    "diagnosis candidate objects, ordered from most to least likely. "
    "Each candidate object must have exactly these nine keys: "
    '"disease_name", "icd10_code" (a string, or null if not confidently '
    'available), "confidence_score" (a number between 0.0 and 1.0), '
    '"clinical_reasoning" (why this diagnosis is supported by the given '
    'clinical evidence), "supporting_findings" (a JSON array of specific '
    'findings that support this diagnosis), "findings_against" (a JSON '
    "array of specific findings that argue against this diagnosis — "
    'never repeat the same finding in both arrays), "recommended_next_tests" '
    "(a JSON array of tests that would help confirm or rule out this "
    'diagnosis), "red_flag_indicators" (a JSON array of any red-flag/'
    "high-risk findings relevant to this diagnosis — empty if none), and "
    '"urgency_level" (one of "routine", "urgent", "emergent" — reflecting '
    "how quickly this diagnosis needs to be addressed if correct).\n\n"
    '2. "serious_diagnoses_not_to_miss": a JSON array of disease names '
    "that are important to rule out given the presentation, even if not "
    "highly probable.\n\n"
    '3. "suggested_investigations": a JSON array of plain-language '
    "investigation recommendations.\n\n"
    '4. "suggested_referrals": a JSON array of plain-language specialist '
    "referral recommendations.\n\n"
    "Only suggest a diagnosis that is clearly supported by the clinical "
    "evidence given to you — never invent a diagnosis, finding, or test "
    "result that was not provided or reasonably inferable from it. If no "
    'diagnosis can be confidently suggested, return an empty "candidates" '
    "array rather than inventing one. Never suggest the same disease name "
    'more than once. Do not include placeholder text such as "[insert]", '
    '"TBD", "XXX", or "Lorem ipsum" anywhere in your response.'
)

_USER_TEMPLATE = (
    "Clinical evidence for differential diagnosis:\n\n"
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
    "Laboratory Results: {{ laboratory_results }}\n"
    "Imaging Summary: {{ imaging_summary }}\n"
    "Clinical Note: {{ clinical_note }}\n"
    "SOAP Note: {{ soap_note }}\n"
    "ICD-10 Suggestions: {{ icd10_suggestions }}\n"
    "Prescription Suggestions: {{ prescription_suggestions }}\n"
    "Allergies: {{ allergies }}\n"
    "Medical Conditions: {{ medical_conditions }}\n\n"
    "Generate a ranked differential diagnosis now."
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
        "laboratory_results",
        "imaging_summary",
        "clinical_note",
        "soap_note",
        "icd10_suggestions",
        "prescription_suggestions",
        "allergies",
        "medical_conditions",
    }
)

_SYSTEM_TEMPLATE_VARIABLES = frozenset({"language"})

_STYLE_GUIDANCE: dict[ClinicalSetting, str] = {
    ClinicalSetting.OUTPATIENT: (
        "You are an expert diagnostic reasoning assistant providing "
        "clinical decision support in {{ language }}, appropriate for a "
        "routine outpatient encounter. Prioritize common, likely "
        "diagnoses first while still flagging any serious diagnoses not "
        "to miss."
    ),
    ClinicalSetting.EMERGENCY: (
        "You are an expert diagnostic reasoning assistant providing "
        "clinical decision support in {{ language }}, appropriate for an "
        "emergency department encounter — prioritize identifying acute, "
        "life-threatening, or time-sensitive diagnoses and their red-flag "
        "indicators above all else."
    ),
    ClinicalSetting.INPATIENT: (
        "You are an expert diagnostic reasoning assistant providing "
        "clinical decision support in {{ language }}, appropriate for an "
        "inpatient admission — consider the evolving clinical picture "
        "and comorbidities across the stay, and flag diagnoses that "
        "would change inpatient management."
    ),
    ClinicalSetting.PEDIATRIC: (
        "You are an expert diagnostic reasoning assistant providing "
        "clinical decision support in {{ language }}, appropriate for a "
        "pediatric patient — consider age-specific differentials and "
        "explicitly flag diagnoses that present differently or are more "
        "urgent in children."
    ),
    ClinicalSetting.GERIATRIC: (
        "You are an expert diagnostic reasoning assistant providing "
        "clinical decision support in {{ language }}, appropriate for a "
        "geriatric patient — consider atypical presentations common in "
        "older adults, polypharmacy-related contributors, and "
        "comorbidity-driven diagnoses."
    ),
}


def system_template_name(clinical_setting: ClinicalSetting) -> str:
    return f"differential_diagnosis_suggestion.{clinical_setting.value}.system"


def developer_template_name(clinical_setting: ClinicalSetting) -> str:
    return f"differential_diagnosis_suggestion.{clinical_setting.value}.developer"


def user_template_name(clinical_setting: ClinicalSetting) -> str:
    return f"differential_diagnosis_suggestion.{clinical_setting.value}.user"


def build_all_templates(*, version: int = 1) -> list[PromptTemplate]:
    """Constructs the full 15-template set (5 settings x system/
    developer/user) at the given version — called once by
    `template_registrar.py`."""
    templates: list[PromptTemplate] = []
    for clinical_setting, guidance in _STYLE_GUIDANCE.items():
        templates.append(
            PromptTemplate(
                name=system_template_name(clinical_setting),
                version=version,
                template_string=guidance,
                variable_names=_SYSTEM_TEMPLATE_VARIABLES,
                description=f"System prompt for {clinical_setting.value} differential diagnosis.",
            )
        )
        templates.append(
            PromptTemplate(
                name=developer_template_name(clinical_setting),
                version=version,
                template_string=_JSON_CONTRACT,
                variable_names=frozenset(),
                description=(
                    f"JSON output contract for {clinical_setting.value} differential diagnosis."
                ),
            )
        )
        templates.append(
            PromptTemplate(
                name=user_template_name(clinical_setting),
                version=version,
                template_string=_USER_TEMPLATE,
                variable_names=_USER_TEMPLATE_VARIABLES,
                description=(
                    f"Clinical evidence prompt for {clinical_setting.value} differential "
                    "diagnosis."
                ),
            )
        )
    return templates

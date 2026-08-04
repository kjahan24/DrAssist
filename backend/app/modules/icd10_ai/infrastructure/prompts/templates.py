"""Production prompt templates for AI ICD-10 Coding — one `(system,
developer, user)` triple per `CodingSetting`, each independently
versioned, registered into AI Foundation's shared `PromptRegistry` by
`template_registrar.py`.

Imports AI Foundation's `domain.value_objects.PromptTemplate` directly
(not `.public`) — the same justified exception
`app.modules.soap_note_ai.infrastructure.prompts.templates`'s own module
docstring documents in full: constructing instances of it to register is
exactly the mechanism `app.modules.ai.container.get_prompt_registry`'s
own docstring anticipates and names for this purpose; nothing in AI
Foundation's own source is modified.

Template names are prefixed `icd10_suggestion`, not `icd10_ai` or
`icd10_coding` — the former would just restate this module's own name,
and the latter is deliberately avoided to prevent any reader confusing an
AI-Foundation `PromptRegistry` entry (a process-lifetime, in-memory
string key, scoped only within AI Foundation) with the pre-existing,
persisted `app.modules.icd10_coding` module (an unrelated, completed
module this task does not touch).

Every `developer` template carries the same fixed JSON-output contract —
a single object with one `"suggestions"` array, each item having exactly
six keys (`icd10_code`, `diagnosis_name`, `confidence_score`,
`clinical_reasoning`, `supporting_evidence`, `flag`) — distinct from
AI SOAP Note Generation's four-section contract, since ICD-10 coding
suggestions are a genuinely different structure (a *list* of items, not a
fixed set of named sections). `system` templates carry setting-specific
tone/priority guidance; `user` templates are the clinical-context
placeholders `infrastructure/prompts/prompt_builder.py` fills in.
"""

from app.modules.ai.domain.value_objects import PromptTemplate
from app.modules.icd10_ai.domain.enums import CodingSetting

_JSON_CONTRACT = (
    "You must respond with ONLY a single JSON object and nothing else — "
    "no markdown code fences, no prose before or after it. The JSON "
    'object must have exactly one key, "suggestions", whose value is a '
    "JSON array of zero or more diagnosis suggestion objects. Each "
    "suggestion object must have exactly these six keys: "
    '"icd10_code" (a syntactically valid ICD-10-CM code, e.g. "J06.9"), '
    '"diagnosis_name" (the plain-English diagnosis name), '
    '"confidence_score" (a number between 0.0 and 1.0), '
    '"clinical_reasoning" (why this diagnosis is supported by the given '
    'clinical information), "supporting_evidence" (which specific '
    'findings, symptoms, or history support it), and "flag" (exactly '
    '"primary" or "secondary"). Only suggest a code that is clearly '
    "supported by the clinical information given to you — never invent a "
    "diagnosis, code, or finding that was not provided or reasonably "
    "inferable from it. If no diagnosis can be confidently suggested from "
    'the given information, return {"suggestions": []} rather than '
    "inventing one. Never suggest the same ICD-10 code more than once. "
    'Do not include placeholder text such as "[insert]", "TBD", "XXX", or '
    '"Lorem ipsum" anywhere in your response.'
)

_USER_TEMPLATE = (
    "Clinical information for ICD-10 coding:\n\n"
    "Patient Age: {{ patient_age }}\n"
    "Patient Sex: {{ patient_sex }}\n"
    "Visit Context: {{ visit_context }}\n"
    "Chief Complaint: {{ chief_complaint }}\n"
    "History of Present Illness: {{ history_of_present_illness }}\n"
    "Symptoms: {{ symptoms }}\n"
    "Review of Systems: {{ review_of_systems }}\n"
    "Physical Examination: {{ physical_examination }}\n"
    "Assessment: {{ assessment }}\n"
    "Plan: {{ plan }}\n"
    "Clinical Note: {{ clinical_note }}\n"
    "SOAP Note: {{ soap_note }}\n"
    "Existing Diagnoses: {{ existing_diagnoses }}\n\n"
    "Suggest ICD-10-CM diagnosis codes now."
)

_USER_TEMPLATE_VARIABLES = frozenset(
    {
        "patient_age",
        "patient_sex",
        "visit_context",
        "chief_complaint",
        "history_of_present_illness",
        "symptoms",
        "review_of_systems",
        "physical_examination",
        "assessment",
        "plan",
        "clinical_note",
        "soap_note",
        "existing_diagnoses",
    }
)

_SYSTEM_TEMPLATE_VARIABLES = frozenset({"language"})

_STYLE_GUIDANCE: dict[CodingSetting, str] = {
    CodingSetting.OUTPATIENT: (
        "You are an expert medical coding assistant. Suggest ICD-10-CM "
        "diagnosis codes in {{ language }} appropriate for a routine "
        "outpatient encounter, prioritizing the most clinically specific "
        "code supported by the documentation."
    ),
    CodingSetting.EMERGENCY: (
        "You are an expert medical coding assistant. Suggest ICD-10-CM "
        "diagnosis codes in {{ language }} appropriate for an emergency "
        "department encounter — prioritize acute, symptom-driven "
        "diagnoses and flag time-sensitive or high-acuity conditions as "
        "primary."
    ),
    CodingSetting.INPATIENT: (
        "You are an expert medical coding assistant. Suggest ICD-10-CM "
        "diagnosis codes in {{ language }} appropriate for an inpatient "
        "admission — consider the full clinical picture, including "
        "comorbidities that affect complexity, and flag the principal "
        "diagnosis driving the admission as primary."
    ),
    CodingSetting.FOLLOW_UP: (
        "You are an expert medical coding assistant. Suggest ICD-10-CM "
        "diagnosis codes in {{ language }} appropriate for a follow-up "
        "visit — prioritize codes reflecting interval change, "
        "resolution, or ongoing management of previously identified "
        "conditions."
    ),
}


def system_template_name(coding_setting: CodingSetting) -> str:
    return f"icd10_suggestion.{coding_setting.value}.system"


def developer_template_name(coding_setting: CodingSetting) -> str:
    return f"icd10_suggestion.{coding_setting.value}.developer"


def user_template_name(coding_setting: CodingSetting) -> str:
    return f"icd10_suggestion.{coding_setting.value}.user"


def build_all_templates(*, version: int = 1) -> list[PromptTemplate]:
    """Constructs the full 12-template set (4 settings x system/
    developer/user) at the given version — called once by
    `template_registrar.py`."""
    templates: list[PromptTemplate] = []
    for coding_setting, guidance in _STYLE_GUIDANCE.items():
        templates.append(
            PromptTemplate(
                name=system_template_name(coding_setting),
                version=version,
                template_string=guidance,
                variable_names=_SYSTEM_TEMPLATE_VARIABLES,
                description=f"System prompt for {coding_setting.value} ICD-10 coding.",
            )
        )
        templates.append(
            PromptTemplate(
                name=developer_template_name(coding_setting),
                version=version,
                template_string=_JSON_CONTRACT,
                variable_names=frozenset(),
                description=f"JSON output contract for {coding_setting.value} ICD-10 coding.",
            )
        )
        templates.append(
            PromptTemplate(
                name=user_template_name(coding_setting),
                version=version,
                template_string=_USER_TEMPLATE,
                variable_names=_USER_TEMPLATE_VARIABLES,
                description=f"Clinical context prompt for {coding_setting.value} ICD-10 coding.",
            )
        )
    return templates

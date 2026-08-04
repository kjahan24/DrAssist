"""Production prompt templates for AI Prescription Assistance — one
`(system, developer, user)` triple per `PrescribingSetting`, each
independently versioned, registered into AI Foundation's shared
`PromptRegistry` by `template_registrar.py`.

Imports AI Foundation's `domain.value_objects.PromptTemplate` directly
(not `.public`) — the same justified exception
`app.modules.icd10_ai.infrastructure.prompts.templates`'s own module
docstring documents in full: constructing instances of it to register is
exactly the mechanism `app.modules.ai.container.get_prompt_registry`'s
own docstring anticipates and names for this purpose; nothing in AI
Foundation's own source is modified.

Template names are prefixed `prescription_suggestion`, not
`prescription_ai` or `prescriptions` — the former would just restate this
module's own name, and the latter is deliberately avoided to prevent any
reader confusing an AI-Foundation `PromptRegistry` entry (a process-
lifetime, in-memory string key, scoped only within AI Foundation) with
the pre-existing, persisted `app.modules.prescriptions` module (an
unrelated, completed module this task does not touch) — the same
precedent `app.modules.icd10_ai.infrastructure.prompts.templates`
establishes relative to `app.modules.icd10_coding`.

Every `developer` template carries the same fixed JSON-output contract:
a `"medications"` array (14 keys per this task's own OUTPUT
specification), a `"safety_findings"` array (the AI's own semantic
medication-safety reasoning — see `MedicationSafetyFinding`'s own
docstring for how this is merged with this module's deterministic
checks), and `"monitoring_recommendations"`/`"follow_up_recommendations"`
string arrays. `system` templates carry setting-specific tone/priority
guidance; `user` templates are the clinical-context placeholders
`infrastructure/prompts/prompt_builder.py` fills in.
"""

from app.modules.ai.domain.value_objects import PromptTemplate
from app.modules.prescription_ai.domain.enums import PrescribingSetting

_JSON_CONTRACT = (
    "You must respond with ONLY a single JSON object and nothing else — "
    "no markdown code fences, no prose before or after it. Every "
    "suggestion you produce is a DRAFT for physician review — never "
    "phrase anything as a final, issued prescription. The JSON object "
    "must have exactly these four keys:\n\n"
    '1. "medications": a JSON array of zero or more medication objects. '
    "Each medication object must have exactly these fourteen keys: "
    '"generic_name", "brand_name" (a string, or null if not applicable), '
    '"strength", "dosage", "route" (e.g. "oral", "iv", "im", "sc", '
    '"topical", "inhalation", "ophthalmic", "otic", "nasal", "rectal", '
    '"vaginal"), "frequency", "duration", "quantity", "is_prn" (true or '
    'false), "clinical_indication", "monitoring_advice", '
    '"patient_instructions", "confidence_score" (a number between 0.0 '
    'and 1.0), and "clinical_reasoning". Every medication must have a '
    "non-empty dosage, frequency, and duration.\n\n"
    '2. "safety_findings": a JSON array of zero or more safety-concern '
    'objects, each with exactly these four keys: "category" (one of '
    '"allergy_conflict", "duplicate_therapy", "contraindication", '
    '"drug_interaction", "pregnancy_risk", "pediatric_dosing", '
    '"geriatric_precaution", "renal_precaution", "hepatic_precaution"), '
    '"severity" (one of "low", "moderate", "high", "critical"), '
    '"description", and "affected_medications" (a JSON array of generic '
    "medication names). Report every safety concern you can identify "
    "from the clinical information given to you, including interactions "
    "with the patient's existing medications and known allergies.\n\n"
    '3. "monitoring_recommendations": a JSON array of plain-language '
    "monitoring recommendation strings.\n\n"
    '4. "follow_up_recommendations": a JSON array of plain-language '
    "follow-up recommendation strings.\n\n"
    "Only suggest a medication that is clearly supported by the clinical "
    "information given to you — never invent a medication, dose, or "
    "finding that was not provided or reasonably inferable from it. If "
    "no medication can be confidently suggested from the given "
    'information, return an empty "medications" array rather than '
    "inventing one. Never suggest the same generic medication more than "
    'once. Do not include placeholder text such as "[insert]", "TBD", '
    '"XXX", or "Lorem ipsum" anywhere in your response.'
)

_USER_TEMPLATE = (
    "Clinical information for prescription assistance:\n\n"
    "Patient Age: {{ patient_age }}\n"
    "Patient Sex: {{ patient_sex }}\n"
    "Pregnancy Status: {{ pregnancy_status }}\n"
    "Weight (kg): {{ weight_kg }}\n"
    "Visit Type: {{ visit_type }}\n"
    "Chief Complaint: {{ chief_complaint }}\n"
    "History of Present Illness: {{ history_of_present_illness }}\n"
    "Symptoms: {{ symptoms }}\n"
    "Review of Systems: {{ review_of_systems }}\n"
    "Physical Examination: {{ physical_examination }}\n"
    "Vitals: {{ vitals }}\n"
    "Assessment: {{ assessment }}\n"
    "Plan: {{ plan }}\n"
    "Clinical Note: {{ clinical_note }}\n"
    "SOAP Note: {{ soap_note }}\n"
    "ICD-10 Suggestions: {{ icd10_suggestions }}\n"
    "Existing Medications: {{ existing_medications }}\n"
    "Allergies: {{ allergies }}\n"
    "Medical Conditions: {{ medical_conditions }}\n"
    "Laboratory Results: {{ laboratory_results }}\n\n"
    "Suggest draft prescription recommendations now."
)

_USER_TEMPLATE_VARIABLES = frozenset(
    {
        "patient_age",
        "patient_sex",
        "pregnancy_status",
        "weight_kg",
        "visit_type",
        "chief_complaint",
        "history_of_present_illness",
        "symptoms",
        "review_of_systems",
        "physical_examination",
        "vitals",
        "assessment",
        "plan",
        "clinical_note",
        "soap_note",
        "icd10_suggestions",
        "existing_medications",
        "allergies",
        "medical_conditions",
        "laboratory_results",
    }
)

_SYSTEM_TEMPLATE_VARIABLES = frozenset({"language"})

_STYLE_GUIDANCE: dict[PrescribingSetting, str] = {
    PrescribingSetting.OUTPATIENT: (
        "You are an expert clinical pharmacology assistant supporting a "
        "physician's DRAFT prescribing decisions in {{ language }}, "
        "appropriate for a routine outpatient encounter. Prioritize "
        "first-line, guideline-concordant therapy and clear patient "
        "instructions."
    ),
    PrescribingSetting.EMERGENCY: (
        "You are an expert clinical pharmacology assistant supporting a "
        "physician's DRAFT prescribing decisions in {{ language }}, "
        "appropriate for an emergency department encounter — prioritize "
        "rapid-onset, acuity-appropriate therapy and flag any "
        "time-sensitive contraindications prominently."
    ),
    PrescribingSetting.INPATIENT: (
        "You are an expert clinical pharmacology assistant supporting a "
        "physician's DRAFT prescribing decisions in {{ language }}, "
        "appropriate for an inpatient admission — consider the full "
        "medication list and comorbidities across the stay, and flag "
        "interactions with the existing inpatient regimen."
    ),
    PrescribingSetting.PEDIATRIC: (
        "You are an expert clinical pharmacology assistant supporting a "
        "physician's DRAFT prescribing decisions in {{ language }}, "
        "appropriate for a pediatric patient — dosing must be weight- "
        "and age-appropriate; explicitly flag pediatric dosing concerns "
        "and medications that are contraindicated or require caution in "
        "children."
    ),
    PrescribingSetting.GERIATRIC: (
        "You are an expert clinical pharmacology assistant supporting a "
        "physician's DRAFT prescribing decisions in {{ language }}, "
        "appropriate for a geriatric patient — consider age-related "
        "renal/hepatic clearance changes, polypharmacy risk, and "
        "medications requiring geriatric caution; prefer lower starting "
        "doses where clinically appropriate."
    ),
    PrescribingSetting.FOLLOW_UP: (
        "You are an expert clinical pharmacology assistant supporting a "
        "physician's DRAFT prescribing decisions in {{ language }}, "
        "appropriate for a follow-up visit — prioritize continuation, "
        "titration, or discontinuation of existing therapy based on "
        "interval response, over starting unrelated new medications."
    ),
}


def system_template_name(prescribing_setting: PrescribingSetting) -> str:
    return f"prescription_suggestion.{prescribing_setting.value}.system"


def developer_template_name(prescribing_setting: PrescribingSetting) -> str:
    return f"prescription_suggestion.{prescribing_setting.value}.developer"


def user_template_name(prescribing_setting: PrescribingSetting) -> str:
    return f"prescription_suggestion.{prescribing_setting.value}.user"


def build_all_templates(*, version: int = 1) -> list[PromptTemplate]:
    """Constructs the full 18-template set (6 settings x system/
    developer/user) at the given version — called once by
    `template_registrar.py`."""
    templates: list[PromptTemplate] = []
    for prescribing_setting, guidance in _STYLE_GUIDANCE.items():
        templates.append(
            PromptTemplate(
                name=system_template_name(prescribing_setting),
                version=version,
                template_string=guidance,
                variable_names=_SYSTEM_TEMPLATE_VARIABLES,
                description=f"System prompt for {prescribing_setting.value} prescribing.",
            )
        )
        templates.append(
            PromptTemplate(
                name=developer_template_name(prescribing_setting),
                version=version,
                template_string=_JSON_CONTRACT,
                variable_names=frozenset(),
                description=f"JSON output contract for {prescribing_setting.value} prescribing.",
            )
        )
        templates.append(
            PromptTemplate(
                name=user_template_name(prescribing_setting),
                version=version,
                template_string=_USER_TEMPLATE,
                variable_names=_USER_TEMPLATE_VARIABLES,
                description=f"Clinical context prompt for {prescribing_setting.value} prescribing.",
            )
        )
    return templates

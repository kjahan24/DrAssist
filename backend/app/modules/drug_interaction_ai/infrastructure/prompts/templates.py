"""Production prompt templates for the AI Drug Interaction & Medication
Safety module — one `(system, developer, user)` triple per
`DrugInteractionSetting`, each independently versioned, registered into
AI Foundation's shared `PromptRegistry` by `template_registrar.py`.

Imports AI Foundation's `domain.value_objects.PromptTemplate` directly
(not `.public`) — the same justified exception every prior AI module's
own `infrastructure/prompts/templates.py` module docstring documents in
full: constructing instances of it to register is exactly the mechanism
`app.modules.ai.container.get_prompt_registry`'s own docstring anticipates
and names for this purpose; nothing in AI Foundation's own source is
modified.

Template names are prefixed `drug_interaction` — no pre-existing,
persisted sibling module shares this name (`app.modules.prescription_ai`
is a distinct, already-completed module this task reuses only through
its own public port — see `container.py`'s own module docstring), so no
further disambiguation is needed.

Every `developer` template carries the same fixed JSON-output contract —
`safety_summary`, `interactions` (an array of `{category, description,
severity, mechanism, clinical_significance, evidence_level,
involved_medications}` objects — this task's own "Interaction List"/
"Interaction Severity"/"Mechanism"/"Clinical Significance"/"Evidence
Level" OUTPUT fields are all represented on this one array's items, per
`DrugInteractionAnalysisResult`'s own docstring), `contraindications`,
`warnings`, `monitoring_recommendations`, `dose_adjustment_suggestions`,
`alternative_medication_suggestions`, `patient_counseling_points`,
`confidence_score`, and `clinical_reasoning` — matching this task's own
OUTPUT specification field-for-field. `system` templates carry
setting-specific tone/priority guidance across this task's own seven
settings (outpatient/inpatient/emergency/icu/pediatric/geriatric/
pregnancy — the richest PROMPTS list of any AI module in this codebase
so far); `user` templates are the medication-list/patient-context
placeholders `infrastructure/prompts/prompt_builder.py` fills in. This
module provides medication-safety decision support only — every
template is explicit that it never autonomously prescribes and never
replaces physician judgment, per this task's own GOAL section.
"""

from app.modules.ai.domain.value_objects import PromptTemplate
from app.modules.drug_interaction_ai.domain.enums import DrugInteractionSetting

_JSON_CONTRACT = (
    "You must respond with ONLY a single JSON object and nothing else — "
    "no markdown code fences, no prose before or after it. You provide "
    "medication safety decision support only — you never autonomously "
    "prescribe medication and you never replace physician judgment. The "
    "JSON object must have exactly these ten keys:\n\n"
    '"safety_summary" (a concise narrative summary of the overall '
    'medication safety picture), "interactions" (a JSON array of '
    'objects, one per detected safety concern, each with "category" — '
    'exactly one of "drug_drug_interaction", "drug_allergy_interaction", '
    '"drug_disease_interaction", "duplicate_therapy", "contraindication", '
    '"black_box_warning", "qt_prolongation_risk", '
    '"serotonin_syndrome_risk", "bleeding_risk", "nephrotoxicity_risk", '
    '"hepatotoxicity_risk", "medication_reconciliation_issue", '
    '"high_risk_elderly_medication", "pediatric_dose_safety", '
    '"pregnancy_safety", "lactation_safety", "renal_dose_adjustment", or '
    '"hepatic_dose_adjustment" — "description", "severity" (exactly '
    'one of "minor", "moderate", "major", or "contraindicated"), '
    '"mechanism" (a string, or null), "clinical_significance" (a '
    'string, or null), "evidence_level" (exactly one of "established", '
    '"probable", "suspected", "theoretical", or null), and '
    '"involved_medications" (a JSON array of the drug names this '
    'concern involves)), "contraindications" and "warnings" (each a '
    'JSON array of strings), "monitoring_recommendations", '
    '"dose_adjustment_suggestions", "alternative_medication_suggestions", '
    'and "patient_counseling_points" (each a JSON array of strings, with '
    'no duplicate entries within the same array), "confidence_score" (a '
    'number between 0.0 and 1.0), and "clinical_reasoning" (a narrative '
    "explanation grounding every interaction and recommendation you made "
    "in the medications and patient context given to you). Only report "
    "interactions, contraindications, or recommendations clearly "
    "supported by the medications and clinical context given to you — "
    "never invent a medication or finding that was not provided or "
    "reasonably inferable from it. Do not include placeholder text such "
    'as "[insert]", "TBD", "XXX", or "Lorem ipsum" anywhere in your '
    "response."
)

_USER_TEMPLATE = (
    "Medication safety analysis request:\n\n"
    "Current Medications: {{ current_medications }}\n"
    "New Prescription: {{ new_prescription }}\n\n"
    "Diagnosis: {{ diagnosis }}\n"
    "Problem List: {{ problem_list }}\n"
    "Allergies: {{ allergies }}\n"
    "Medical Conditions: {{ medical_conditions }}\n"
    "Pregnancy Status: {{ pregnancy_status }}\n"
    "Lactation Status: {{ lactation_status }}\n"
    "Patient Age: {{ patient_age }}\n"
    "Patient Weight (kg): {{ patient_weight_kg }}\n"
    "Renal Function: {{ renal_function }}\n"
    "Liver Function: {{ hepatic_function }}\n"
    "Recent Laboratory Values: {{ recent_lab_values }}\n\n"
    "Produce a structured medication safety analysis now."
)

_USER_TEMPLATE_VARIABLES = frozenset(
    {
        "current_medications",
        "new_prescription",
        "diagnosis",
        "problem_list",
        "allergies",
        "medical_conditions",
        "pregnancy_status",
        "lactation_status",
        "patient_age",
        "patient_weight_kg",
        "renal_function",
        "hepatic_function",
        "recent_lab_values",
    }
)

_SYSTEM_TEMPLATE_VARIABLES = frozenset({"language"})

_STYLE_GUIDANCE: dict[DrugInteractionSetting, str] = {
    DrugInteractionSetting.OUTPATIENT: (
        "You are an expert medication safety engine producing structured "
        "clinical decision-support in {{ language }}, appropriate for a "
        "routine outpatient encounter. Ground every finding in the "
        "medications and context given to you."
    ),
    DrugInteractionSetting.INPATIENT: (
        "You are an expert medication safety engine producing structured "
        "clinical decision-support in {{ language }}, appropriate for an "
        "inpatient admission — weigh the evolving medication list and "
        "highlight anything that would change inpatient management or "
        "monitoring."
    ),
    DrugInteractionSetting.EMERGENCY: (
        "You are an expert medication safety engine producing structured "
        "clinical decision-support in {{ language }}, appropriate for an "
        "emergency department encounter — prioritize identifying "
        "contraindicated or major interactions requiring immediate "
        "attention above all else."
    ),
    DrugInteractionSetting.ICU: (
        "You are an expert medication safety engine producing structured "
        "clinical decision-support in {{ language }}, appropriate for a "
        "critically ill ICU patient — weigh organ-support therapies, "
        "narrow therapeutic-index medications, and rapidly changing renal "
        "or hepatic function carefully."
    ),
    DrugInteractionSetting.PEDIATRIC: (
        "You are an expert medication safety engine producing structured "
        "clinical decision-support in {{ language }}, appropriate for a "
        "pediatric patient — consider weight-based dosing and explicitly "
        "flag medications that are unsafe or present differently in "
        "children."
    ),
    DrugInteractionSetting.GERIATRIC: (
        "You are an expert medication safety engine producing structured "
        "clinical decision-support in {{ language }}, appropriate for a "
        "geriatric patient — consider polypharmacy, high-risk elderly "
        "medications, and age-related renal/hepatic changes carefully."
    ),
    DrugInteractionSetting.PREGNANCY: (
        "You are an expert medication safety engine producing structured "
        "clinical decision-support in {{ language }}, appropriate for a "
        "pregnant or lactating patient — weigh pregnancy and lactation "
        "safety carefully for every medication given to you."
    ),
}


def system_template_name(medication_setting: DrugInteractionSetting) -> str:
    return f"drug_interaction.{medication_setting.value}.system"


def developer_template_name(medication_setting: DrugInteractionSetting) -> str:
    return f"drug_interaction.{medication_setting.value}.developer"


def user_template_name(medication_setting: DrugInteractionSetting) -> str:
    return f"drug_interaction.{medication_setting.value}.user"


def build_all_templates(*, version: int = 1) -> list[PromptTemplate]:
    """Constructs the full 21-template set (7 settings x system/
    developer/user) at the given version — called once by
    `template_registrar.py`."""
    templates: list[PromptTemplate] = []
    for medication_setting, guidance in _STYLE_GUIDANCE.items():
        templates.append(
            PromptTemplate(
                name=system_template_name(medication_setting),
                version=version,
                template_string=guidance,
                variable_names=_SYSTEM_TEMPLATE_VARIABLES,
                description=f"System prompt for {medication_setting.value} medication safety.",
            )
        )
        templates.append(
            PromptTemplate(
                name=developer_template_name(medication_setting),
                version=version,
                template_string=_JSON_CONTRACT,
                variable_names=frozenset(),
                description=(
                    f"JSON output contract for {medication_setting.value} medication safety."
                ),
            )
        )
        templates.append(
            PromptTemplate(
                name=user_template_name(medication_setting),
                version=version,
                template_string=_USER_TEMPLATE,
                variable_names=_USER_TEMPLATE_VARIABLES,
                description=(
                    f"Medication list prompt for {medication_setting.value} medication safety."
                ),
            )
        )
    return templates

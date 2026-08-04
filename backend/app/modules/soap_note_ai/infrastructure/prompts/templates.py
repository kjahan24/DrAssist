"""Production prompt templates for AI SOAP Note Generation — one
`(system, developer, user)` triple per `SOAPStyle`, each independently
versioned, registered into AI Foundation's shared `PromptRegistry` by
`template_registrar.py`.

Imports AI Foundation's `domain.value_objects.PromptTemplate` directly
(not `.public`) — the same justified exception
`app.modules.clinical_note_ai.infrastructure.prompts.templates`'s own
module docstring documents in full: constructing instances of it to
register is exactly the mechanism `app.modules.ai.container
.get_prompt_registry`'s own docstring anticipates and names for this
purpose; nothing in AI Foundation's own source is modified.

Every `developer` template carries the same fixed JSON-output contract
(four keys — "subjective", "objective", "assessment", "plan" — distinct
from AI Clinical Note Generation's six-key contract, since SOAP notes are
a genuinely different structure, not a subset). `system` templates carry
style-specific tone/length guidance; `user` templates are the encounter-
data placeholders `infrastructure/prompts/prompt_builder.py` fills in.
"""

from app.modules.ai.domain.value_objects import PromptTemplate
from app.modules.soap_note_ai.domain.enums import SOAPStyle

_JSON_CONTRACT = (
    "You must respond with ONLY a single JSON object and nothing else — "
    "no markdown code fences, no prose before or after it. The JSON object "
    "must have exactly these four string-valued keys, in this order: "
    '"subjective", "objective", "assessment", "plan". Every value must be '
    "clinically accurate prose grounded only in the information given to "
    "you in the user message — never invent findings, medications, or "
    "diagnoses that were not provided. The Subjective and Objective "
    "sections must describe genuinely different content — never repeat the "
    "same sentence across sections. If information for a section is not "
    'available, write "Not documented." for that section rather than '
    "inventing content. Do not include placeholder text such as "
    '"[insert]", "TBD", "XXX", or "Lorem ipsum" anywhere in your response.'
)

_USER_TEMPLATE = (
    "Patient encounter details:\n\n"
    "Patient Age: {{ patient_age }}\n"
    "Patient Sex: {{ patient_sex }}\n"
    "Visit Type: {{ visit_type }}\n"
    "Chief Complaint: {{ chief_complaint }}\n"
    "History of Present Illness: {{ history_of_present_illness }}\n"
    "Symptoms: {{ symptoms }}\n"
    "Review of Systems: {{ review_of_systems }}\n"
    "Physical Examination: {{ physical_examination }}\n"
    "Vitals: {{ vitals }}\n"
    "Current Medications: {{ medications }}\n"
    "Known Allergies: {{ allergies }}\n"
    "Diagnoses: {{ diagnoses }}\n"
    "Assessment (clinician-provided): {{ assessment }}\n"
    "Plan (clinician-provided): {{ plan }}\n"
    "Clinician Instructions: {{ clinician_instructions }}\n"
    "Encounter Context: {{ encounter_context }}\n\n"
    "Generate the structured SOAP note now."
)

_USER_TEMPLATE_VARIABLES = frozenset(
    {
        "patient_age",
        "patient_sex",
        "visit_type",
        "chief_complaint",
        "history_of_present_illness",
        "symptoms",
        "review_of_systems",
        "physical_examination",
        "vitals",
        "medications",
        "allergies",
        "diagnoses",
        "assessment",
        "plan",
        "clinician_instructions",
        "encounter_context",
    }
)

_SYSTEM_TEMPLATE_VARIABLES = frozenset({"language"})

_STYLE_GUIDANCE: dict[SOAPStyle, str] = {
    SOAPStyle.CONCISE: (
        "You are an expert clinical documentation assistant. Draft a "
        "concise SOAP note in {{ language }}, using brief, efficient "
        "phrasing appropriate for a busy practice. Prioritize brevity — "
        "one to three sentences per section wherever clinically adequate, "
        "while still covering Subjective, Objective, Assessment, and Plan."
    ),
    SOAPStyle.STANDARD: (
        "You are an expert clinical documentation assistant. Draft a "
        "standard SOAP note in {{ language }}, using balanced phrasing "
        "appropriate for routine clinical documentation — neither overly "
        "terse nor overly verbose."
    ),
    SOAPStyle.DETAILED: (
        "You are an expert clinical documentation assistant. Draft a "
        "thorough, detailed SOAP note in {{ language }}, using "
        "comprehensive phrasing appropriate for a complex case. Capture "
        "clinical nuance and reasoning in each section rather than "
        "summarizing tersely."
    ),
    SOAPStyle.EMERGENCY: (
        "You are an expert clinical documentation assistant. Draft a SOAP "
        "note in {{ language }} appropriate for an emergency department "
        "encounter — prioritize acuity, red-flag findings, time-"
        "sensitivity, and disposition-relevant details in every section."
    ),
    SOAPStyle.FOLLOW_UP: (
        "You are an expert clinical documentation assistant. Draft a SOAP "
        "note in {{ language }} appropriate for a follow-up visit — "
        "emphasize interval change since the prior encounter and response "
        "to the ongoing treatment plan wherever the provided information "
        "supports it."
    ),
}


def system_template_name(soap_style: SOAPStyle) -> str:
    return f"soap_note.{soap_style.value}.system"


def developer_template_name(soap_style: SOAPStyle) -> str:
    return f"soap_note.{soap_style.value}.developer"


def user_template_name(soap_style: SOAPStyle) -> str:
    return f"soap_note.{soap_style.value}.user"


def build_all_templates(*, version: int = 1) -> list[PromptTemplate]:
    """Constructs the full 15-template set (5 styles x system/developer/
    user) at the given version — called once by `template_registrar.py`.
    """
    templates: list[PromptTemplate] = []
    for soap_style, guidance in _STYLE_GUIDANCE.items():
        templates.append(
            PromptTemplate(
                name=system_template_name(soap_style),
                version=version,
                template_string=guidance,
                variable_names=_SYSTEM_TEMPLATE_VARIABLES,
                description=f"System prompt for {soap_style.value} SOAP notes.",
            )
        )
        templates.append(
            PromptTemplate(
                name=developer_template_name(soap_style),
                version=version,
                template_string=_JSON_CONTRACT,
                variable_names=frozenset(),
                description=f"JSON output contract for {soap_style.value} SOAP notes.",
            )
        )
        templates.append(
            PromptTemplate(
                name=user_template_name(soap_style),
                version=version,
                template_string=_USER_TEMPLATE,
                variable_names=_USER_TEMPLATE_VARIABLES,
                description=f"Encounter data prompt for {soap_style.value} SOAP notes.",
            )
        )
    return templates

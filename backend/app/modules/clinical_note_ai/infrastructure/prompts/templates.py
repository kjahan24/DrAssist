"""Production prompt templates for AI Clinical Note Generation — one
`(system, developer, user)` triple per `NoteStyle`, each independently
versioned, registered into AI Foundation's shared `PromptRegistry` by
`template_registrar.py`.

Imports AI Foundation's `domain.value_objects.PromptTemplate` directly
(not `.public`) — `PromptTemplate` is not part of that module's public
surface, but constructing instances of it to register is exactly the
mechanism `app.modules.ai.container.get_prompt_registry`'s own docstring
anticipates and names for this exact purpose ("a future clinical module
registers its own templates via `PromptRegistry.register()` at its own
`container.py` import time") — see this module's own `container.py` for
where registration actually happens; nothing in AI Foundation's own
source is modified to enable this.

Every `developer` template carries the same fixed JSON-output contract
(all five copies are identical text today, versioned independently per
style anyway — see `template_selector.py`'s own docstring for why).
`system` templates carry style-specific tone/length guidance; `user`
templates are the encounter-data placeholders `infrastructure/prompts
/prompt_builder.py` fills in.
"""

from app.modules.ai.domain.value_objects import PromptTemplate
from app.modules.clinical_note_ai.domain.enums import NoteStyle

_JSON_CONTRACT = (
    "You must respond with ONLY a single JSON object and nothing else — "
    "no markdown code fences, no prose before or after it. The JSON object "
    "must have exactly these six string-valued keys, in this order: "
    '"chief_complaint", "history_of_present_illness", "review_of_systems", '
    '"physical_examination", "assessment", "plan". Every value must be '
    "clinically accurate prose grounded only in the information given to "
    "you in the user message — never invent findings, medications, or "
    "diagnoses that were not provided. If information for a section is not "
    'available, write "Not documented." for that section rather than '
    "inventing content. Do not include placeholder text such as "
    '"[insert]", "TBD", "XXX", or "Lorem ipsum" anywhere in your response.'
)

_USER_TEMPLATE = (
    "Patient encounter details:\n\n"
    "Chief Complaint: {{ chief_complaint }}\n"
    "History of Present Illness: {{ history_of_present_illness }}\n"
    "Symptoms: {{ symptoms }}\n"
    "Observations: {{ observations }}\n"
    "Physical Examination: {{ physical_examination }}\n"
    "Assessment (clinician-provided): {{ assessment }}\n"
    "Plan (clinician-provided): {{ plan }}\n"
    "Current Medications: {{ medications }}\n"
    "Known Allergies: {{ allergies }}\n"
    "Vitals: {{ vitals }}\n"
    "Diagnoses: {{ diagnoses }}\n"
    "Clinician Instructions: {{ clinician_instructions }}\n"
    "Encounter Context: {{ encounter_context }}\n\n"
    "Generate the structured clinical note now."
)

_USER_TEMPLATE_VARIABLES = frozenset(
    {
        "chief_complaint",
        "history_of_present_illness",
        "symptoms",
        "observations",
        "physical_examination",
        "assessment",
        "plan",
        "medications",
        "allergies",
        "vitals",
        "diagnoses",
        "clinician_instructions",
        "encounter_context",
    }
)

_SYSTEM_TEMPLATE_VARIABLES = frozenset({"language"})

_STYLE_GUIDANCE: dict[NoteStyle, str] = {
    NoteStyle.CONCISE: (
        "You are an expert clinical documentation assistant. Draft a concise "
        "clinical note in {{ language }}, using brief, efficient phrasing "
        "appropriate for a busy practice. Prioritize brevity — one to three "
        "sentences per section wherever clinically adequate, while still "
        "covering every section."
    ),
    NoteStyle.DETAILED: (
        "You are an expert clinical documentation assistant. Draft a "
        "thorough, detailed clinical note in {{ language }}, using "
        "comprehensive phrasing appropriate for a complex case. Capture "
        "clinical nuance and reasoning in each section rather than "
        "summarizing tersely."
    ),
    NoteStyle.EMERGENCY: (
        "You are an expert clinical documentation assistant. Draft a "
        "clinical note in {{ language }} appropriate for an emergency "
        "department encounter — prioritize acuity, red-flag findings, "
        "time-sensitivity, and disposition-relevant details in every "
        "section."
    ),
    NoteStyle.OUTPATIENT: (
        "You are an expert clinical documentation assistant. Draft a "
        "clinical note in {{ language }} appropriate for a routine "
        "outpatient visit, reflecting standard primary or specialty care "
        "documentation conventions."
    ),
    NoteStyle.FOLLOW_UP: (
        "You are an expert clinical documentation assistant. Draft a "
        "clinical note in {{ language }} appropriate for a follow-up "
        "visit — emphasize interval change since the prior encounter and "
        "response to the ongoing treatment plan wherever the provided "
        "information supports it."
    ),
}


def system_template_name(note_style: NoteStyle) -> str:
    return f"clinical_note.{note_style.value}.system"


def developer_template_name(note_style: NoteStyle) -> str:
    return f"clinical_note.{note_style.value}.developer"


def user_template_name(note_style: NoteStyle) -> str:
    return f"clinical_note.{note_style.value}.user"


def build_all_templates(*, version: int = 1) -> list[PromptTemplate]:
    """Constructs the full 15-template set (5 styles x system/developer/
    user) at the given version — called once by `template_registrar.py`.
    """
    templates: list[PromptTemplate] = []
    for note_style, guidance in _STYLE_GUIDANCE.items():
        templates.append(
            PromptTemplate(
                name=system_template_name(note_style),
                version=version,
                template_string=guidance,
                variable_names=_SYSTEM_TEMPLATE_VARIABLES,
                description=f"System prompt for {note_style.value} clinical notes.",
            )
        )
        templates.append(
            PromptTemplate(
                name=developer_template_name(note_style),
                version=version,
                template_string=_JSON_CONTRACT,
                variable_names=frozenset(),
                description=f"JSON output contract for {note_style.value} clinical notes.",
            )
        )
        templates.append(
            PromptTemplate(
                name=user_template_name(note_style),
                version=version,
                template_string=_USER_TEMPLATE,
                variable_names=_USER_TEMPLATE_VARIABLES,
                description=f"Encounter data prompt for {note_style.value} clinical notes.",
            )
        )
    return templates

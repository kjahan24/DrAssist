"""Prompt templates for the Community AI Features module's three
chat-completion-based analyses (summary, misinformation, resource
recommendation) — registered into AI Foundation's shared `PromptRegistry`
by `template_registrar.py`, rendered via `AIGatewayPort.render_prompt`,
never interpolated with an f-string directly, mirroring every `*_ai`
module's own `infrastructure/prompts/templates.py` shape (e.g.
`app.modules.icd10_ai.infrastructure.prompts.templates`).

Every template's own instructions make explicit that this is
**AI-generated analysis, not verified medical information, and never a
diagnosis or treatment recommendation** — this task's own SAFETY section
("Clearly distinguish AI-generated analysis from verified medical
information", "Avoid making diagnosis/treatment decisions") is enforced
partly by the prompt itself (asking the model to stay in this lane), and
partly structurally (`CommunityDiscussionSummary.safety_disclaimer`/
`MisinformationAssessment.explanation` are always surfaced alongside the
result, never silently dropped — see `presentation/schemas.py`).

None of these templates ever include the target's own `author_id` or any
other identity field — see `application/services/_target_resolution.py`
's own docstring: only `title`/`text` (already-published, community-
visible content) are ever passed in, regardless of `is_anonymous`.

`build_all_templates()` returns the `PromptTemplate` value objects
`template_registrar.py` registers — imported from `app.modules.ai.domain
.value_objects`, the one narrow, established exception to "never import
from `app.modules.ai.domain`/`.infrastructure`" every `*_ai` module's own
`infrastructure/prompts/template_registrar.py` already relies on:
`AIGatewayPort` exposes no public method to *register* a template (only
`render_prompt`, which renders an already-registered one), so reaching
into `PromptRegistry`/`PromptTemplate` directly is the only way any
feature module can add its own prompts at all.
"""

from app.modules.ai.domain.value_objects import PromptTemplate

_SYSTEM_PREAMBLE = (
    "You are a medical-community discussion analysis assistant. Your output is "
    "advisory AI-generated analysis, never verified medical information, a "
    "diagnosis, or a treatment recommendation. You must respond with a single "
    "JSON object and nothing else — no markdown fences, no commentary."
)

SUMMARY_SYSTEM_TEMPLATE_NAME = "community_ai.summary.system"
SUMMARY_USER_TEMPLATE_NAME = "community_ai.summary.user"
SUMMARY_TEMPLATE_VERSION = 1

_SUMMARY_SYSTEM_TEMPLATE = (
    _SYSTEM_PREAMBLE + " Summarize the given medical community discussion. Respond with exactly "
    "this JSON shape: "
    '{"key_points": [string, ...], "main_claims": [string, ...], '
    '"areas_of_agreement": [string, ...], "areas_of_disagreement": [string, ...], '
    '"unanswered_questions": [string, ...], "safety_disclaimer": string or null}. '
    "Include a safety_disclaimer whenever the discussion touches diagnosis, "
    "treatment, medication, or dosage; otherwise use null. Any list may be "
    "empty. Never invent claims the discussion does not actually contain."
)

_SUMMARY_USER_TEMPLATE = "Title: {{ title }}\n\nDiscussion:\n{{ text }}"


MISINFORMATION_SYSTEM_TEMPLATE_NAME = "community_ai.misinformation.system"
MISINFORMATION_USER_TEMPLATE_NAME = "community_ai.misinformation.user"
MISINFORMATION_TEMPLATE_VERSION = 1

_MISINFORMATION_SYSTEM_TEMPLATE = (
    _SYSTEM_PREAMBLE + " Assess the given medical community discussion for potentially "
    "misleading or unsupported medical claims. Respond with exactly this JSON "
    "shape: "
    '{"risk_level": "low" | "medium" | "high" | "critical", '
    '"claims": [string, ...], "evidence_needed": boolean, '
    '"explanation": string, "confidence_score": number between 0 and 1, '
    '"recommended_for_moderation_review": boolean, '
    '"reference_suggestions": [string, ...]}. '
    'Use "critical" only for claims that could cause immediate serious '
    "harm if followed (e.g. dangerous dosing, discouraging emergency care). "
    "Set recommended_for_moderation_review to true whenever risk_level is "
    '"high" or "critical". This assessment is advisory only — it must never '
    "be treated as an automatic takedown decision."
)

_MISINFORMATION_USER_TEMPLATE = "Title: {{ title }}\n\nDiscussion:\n{{ text }}"


RESOURCE_RECOMMENDATION_SYSTEM_TEMPLATE_NAME = "community_ai.resource_recommendation.system"
RESOURCE_RECOMMENDATION_USER_TEMPLATE_NAME = "community_ai.resource_recommendation.user"
RESOURCE_RECOMMENDATION_TEMPLATE_VERSION = 1

_RESOURCE_RECOMMENDATION_SYSTEM_TEMPLATE = (
    _SYSTEM_PREAMBLE + " You will be given a medical community discussion and a fixed catalog "
    "of trusted medical resources. Select and rank only from the sources "
    "listed in the catalog — you must never invent a source, title, or URL "
    "that is not in the catalog. Respond with exactly this JSON shape: "
    '{"items": [{"source_title": string, "source_url": string, '
    '"resource_type": string, "relevance_explanation": string, '
    '"confidence_score": number between 0 and 1}, ...]}. '
    "source_title and source_url must be copied exactly from the catalog "
    "entry you are recommending. Include only sources genuinely relevant to "
    "the discussion; it is fine to return an empty list if none are relevant."
)

_RESOURCE_RECOMMENDATION_USER_TEMPLATE = (
    "Title: {{ title }}\n\nDiscussion:\n{{ text }}\n\nCatalog:\n{{ catalog }}"
)


def build_all_templates() -> list[PromptTemplate]:
    return [
        PromptTemplate(
            name=SUMMARY_SYSTEM_TEMPLATE_NAME,
            version=SUMMARY_TEMPLATE_VERSION,
            template_string=_SUMMARY_SYSTEM_TEMPLATE,
            variable_names=frozenset(),
            description="System instructions for discussion summarization.",
        ),
        PromptTemplate(
            name=SUMMARY_USER_TEMPLATE_NAME,
            version=SUMMARY_TEMPLATE_VERSION,
            template_string=_SUMMARY_USER_TEMPLATE,
            variable_names=frozenset({"title", "text"}),
            description="User content for discussion summarization.",
        ),
        PromptTemplate(
            name=MISINFORMATION_SYSTEM_TEMPLATE_NAME,
            version=MISINFORMATION_TEMPLATE_VERSION,
            template_string=_MISINFORMATION_SYSTEM_TEMPLATE,
            variable_names=frozenset(),
            description="System instructions for misinformation risk assessment.",
        ),
        PromptTemplate(
            name=MISINFORMATION_USER_TEMPLATE_NAME,
            version=MISINFORMATION_TEMPLATE_VERSION,
            template_string=_MISINFORMATION_USER_TEMPLATE,
            variable_names=frozenset({"title", "text"}),
            description="User content for misinformation risk assessment.",
        ),
        PromptTemplate(
            name=RESOURCE_RECOMMENDATION_SYSTEM_TEMPLATE_NAME,
            version=RESOURCE_RECOMMENDATION_TEMPLATE_VERSION,
            template_string=_RESOURCE_RECOMMENDATION_SYSTEM_TEMPLATE,
            variable_names=frozenset(),
            description="System instructions for trusted resource recommendation.",
        ),
        PromptTemplate(
            name=RESOURCE_RECOMMENDATION_USER_TEMPLATE_NAME,
            version=RESOURCE_RECOMMENDATION_TEMPLATE_VERSION,
            template_string=_RESOURCE_RECOMMENDATION_USER_TEMPLATE,
            variable_names=frozenset({"title", "text", "catalog"}),
            description="User content for trusted resource recommendation.",
        ),
    ]

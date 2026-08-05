"""A small order-preserving dedupe helper shared by this module's own
application services (`risk_explanation_service.py`,
`monitoring_recommendation_service.py`) — an intra-module helper, not a
`app/shared/` addition: it is specific to this module's own
`tuple[str, ...]`-shaped output fields, the same "small intra-module
helper" scope every prior AI module's own equivalent (e.g.
`app.modules.drug_interaction_ai.application.services
.alternative_medication_service.AlternativeMedicationService.deduplicate`)
serves for itself, minus the ceremony of a full service class since no
part of this task names a deduplication service of its own.
"""


def dedupe_preserving_order(items: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return tuple(result)

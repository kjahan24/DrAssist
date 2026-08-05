"""A small order-preserving dedupe helper shared by this module's own
application services — an intra-module helper, not a `app/shared/`
addition: it is specific to this module's own `tuple[str, ...]`-shaped
output fields, the same "small intra-module helper" scope
`app.modules.risk_stratification_ai.application.services._dedupe
.dedupe_preserving_order` establishes for its own, identical need.
"""


def dedupe_preserving_order(items: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return tuple(result)

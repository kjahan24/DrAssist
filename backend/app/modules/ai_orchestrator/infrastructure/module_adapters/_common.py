"""Small helpers shared by every concrete `WorkflowExecutorPort` adapter
in this package — intra-module only (not `app.shared`, since these are
specific to this module's own `WorkflowExecutionInput`/`context` shapes,
the same "small intra-module helper" scope
`app.modules.risk_stratification_ai.application.services._dedupe
.dedupe_preserving_order` establishes for its own, analogous need).
"""

from collections.abc import Mapping

from app.modules.ai_orchestrator.domain.enums import WorkflowModule


def join_or_none(items: tuple[str, ...]) -> str | None:
    return "; ".join(items) if items else None


def upstream_summary(context: Mapping[WorkflowModule, str], module: WorkflowModule) -> str | None:
    return context.get(module)

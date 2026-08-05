"""Unit tests for the small helpers every concrete `WorkflowExecutorPort`
adapter shares: `join_or_none` and `upstream_summary`."""

from app.modules.ai_orchestrator.domain.enums import WorkflowModule
from app.modules.ai_orchestrator.infrastructure.module_adapters._common import (
    join_or_none,
    upstream_summary,
)


class TestJoinOrNone:
    def test_empty_tuple_returns_none(self) -> None:
        assert join_or_none(()) is None

    def test_single_item_returns_that_item(self) -> None:
        assert join_or_none(("only finding",)) == "only finding"

    def test_multiple_items_are_joined_with_semicolons(self) -> None:
        assert join_or_none(("first", "second", "third")) == "first; second; third"


class TestUpstreamSummary:
    def test_returns_none_when_module_not_in_context(self) -> None:
        assert upstream_summary({}, WorkflowModule.CLINICAL_NOTE) is None

    def test_returns_the_context_value_for_the_given_module(self) -> None:
        context = {WorkflowModule.CLINICAL_NOTE: "clinical note summary"}
        assert upstream_summary(context, WorkflowModule.CLINICAL_NOTE) == "clinical note summary"

    def test_does_not_return_a_different_modules_value(self) -> None:
        context = {WorkflowModule.SOAP_NOTE: "soap note summary"}
        assert upstream_summary(context, WorkflowModule.CLINICAL_NOTE) is None

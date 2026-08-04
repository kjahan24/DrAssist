"""Unit tests for `container.py`'s DI wiring.

`build_clinical_copilot_facade(session)` is exercised with a dummy stand-in
for `AsyncSession` — every repository the seven peer modules' own
`build_*_facade` functions construct only *stores* the session reference
at construction time (confirmed against
`app.modules.patient.container.build_patient_facade`'s own implementation);
no query executes until a repository method is actually awaited, so this
test can verify the wiring succeeds without a live database.
"""

from app.modules.ai_copilot.container import (
    build_clinical_copilot_facade,
    get_copilot_audit_logger,
    get_cost_estimator,
    get_output_parser,
    get_response_validator,
)
from app.modules.ai_copilot.public.facade import ClinicalCopilotFacade

_DUMMY_SESSION = object()


class TestBuildClinicalCopilotFacade:
    def test_returns_a_clinical_copilot_facade(self) -> None:
        facade = build_clinical_copilot_facade(_DUMMY_SESSION)  # type: ignore[arg-type]
        assert isinstance(facade, ClinicalCopilotFacade)

    def test_each_call_builds_a_fresh_facade(self) -> None:
        first = build_clinical_copilot_facade(_DUMMY_SESSION)  # type: ignore[arg-type]
        second = build_clinical_copilot_facade(_DUMMY_SESSION)  # type: ignore[arg-type]
        assert first is not second


class TestSingletonHelpers:
    def test_output_parser_is_a_singleton(self) -> None:
        assert get_output_parser() is get_output_parser()

    def test_response_validator_is_a_singleton(self) -> None:
        assert get_response_validator() is get_response_validator()

    def test_copilot_audit_logger_is_a_singleton(self) -> None:
        assert get_copilot_audit_logger() is get_copilot_audit_logger()

    def test_cost_estimator_is_a_singleton(self) -> None:
        assert get_cost_estimator() is get_cost_estimator()

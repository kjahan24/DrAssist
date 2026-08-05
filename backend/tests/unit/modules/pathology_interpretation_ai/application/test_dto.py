"""Unit tests for `GeneratedPathologyInterpretation`."""

from app.modules.pathology_interpretation_ai.application.dto import (
    GeneratedPathologyInterpretation,
)
from tests.unit.modules.pathology_interpretation_ai.application.fakes import (
    make_generation_session,
    make_result,
)


class TestGeneratedPathologyInterpretation:
    def test_bundles_result_and_session(self) -> None:
        result = make_result()
        session = make_generation_session()

        generated = GeneratedPathologyInterpretation(result=result, session=session)

        assert generated.result is result
        assert generated.session is session

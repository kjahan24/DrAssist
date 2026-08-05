"""Unit tests for `GeneratedRadiologyInterpretation`."""

from app.modules.radiology_interpretation_ai.application.dto import (
    GeneratedRadiologyInterpretation,
)
from tests.unit.modules.radiology_interpretation_ai.application.fakes import (
    make_generation_session,
    make_result,
)


class TestGeneratedRadiologyInterpretation:
    def test_bundles_result_and_session(self) -> None:
        result = make_result()
        session = make_generation_session()

        generated = GeneratedRadiologyInterpretation(result=result, session=session)

        assert generated.result is result
        assert generated.session is session

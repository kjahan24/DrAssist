"""Unit tests for `GeneratedLabInterpretation`."""

from app.modules.lab_interpretation_ai.application.dto import GeneratedLabInterpretation
from tests.unit.modules.lab_interpretation_ai.application.fakes import (
    make_generation_session,
    make_result,
)


class TestGeneratedLabInterpretation:
    def test_bundles_result_and_session(self) -> None:
        result = make_result()
        session = make_generation_session()

        generated = GeneratedLabInterpretation(result=result, session=session)

        assert generated.result is result
        assert generated.session is session

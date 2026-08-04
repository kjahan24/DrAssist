"""Unit tests for the AI Medical Reasoning Engine's application DTOs."""

from app.modules.medical_reasoning_ai.application.dto import GeneratedMedicalReasoning
from tests.unit.modules.medical_reasoning_ai.application.fakes import (
    make_generation_session,
    make_result,
)


class TestGeneratedMedicalReasoning:
    def test_bundles_result_and_session(self) -> None:
        result = make_result()
        session = make_generation_session()

        generated = GeneratedMedicalReasoning(result=result, session=session)

        assert generated.result is result
        assert generated.session is session

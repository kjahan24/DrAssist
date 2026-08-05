"""Unit tests for `GeneratedDrugInteractionAnalysis`."""

from app.modules.drug_interaction_ai.application.dto import GeneratedDrugInteractionAnalysis
from tests.unit.modules.drug_interaction_ai.application.fakes import (
    make_generation_session,
    make_result,
)


class TestGeneratedDrugInteractionAnalysis:
    def test_bundles_result_and_session(self) -> None:
        result = make_result()
        session = make_generation_session()

        generated = GeneratedDrugInteractionAnalysis(result=result, session=session)

        assert generated.result is result
        assert generated.session is session

"""Tests for the application-layer `GeneratedRiskStratification` DTO."""

from app.modules.risk_stratification_ai.application.dto import GeneratedRiskStratification
from tests.unit.modules.risk_stratification_ai.application.fakes import (
    make_generation_session,
    make_result,
)


class TestGeneratedRiskStratification:
    def test_construction_bundles_result_and_session(self) -> None:
        result = make_result()
        session = make_generation_session()

        generated = GeneratedRiskStratification(result=result, session=session)

        assert generated.result is result
        assert generated.session is session

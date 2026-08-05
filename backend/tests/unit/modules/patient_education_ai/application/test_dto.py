"""Tests for the application-layer `GeneratedPatientEducation` DTO."""

from app.modules.patient_education_ai.application.dto import GeneratedPatientEducation
from tests.unit.modules.patient_education_ai.application.fakes import (
    make_generation_session,
    make_result,
)


class TestGeneratedPatientEducation:
    def test_construction_bundles_result_and_session(self) -> None:
        result = make_result()
        session = make_generation_session()

        generated = GeneratedPatientEducation(result=result, session=session)

        assert generated.result is result
        assert generated.session is session

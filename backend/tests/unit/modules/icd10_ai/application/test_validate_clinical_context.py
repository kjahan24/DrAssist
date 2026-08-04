"""Unit tests for `ValidateClinicalContextUseCase`."""

from uuid import uuid4

from app.modules.icd10_ai.application.use_cases.validate_clinical_context import (
    ValidateClinicalContextUseCase,
)
from app.modules.icd10_ai.domain.enums import CodingSetting
from app.modules.icd10_ai.domain.value_objects import ICD10CodingInput


def _coding_input(**overrides: object) -> ICD10CodingInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Sore throat",
        "coding_setting": CodingSetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return ICD10CodingInput(**defaults)  # type: ignore[arg-type]


class TestValidateClinicalContextUseCase:
    async def test_is_always_valid(self) -> None:
        use_case = ValidateClinicalContextUseCase()

        result = await use_case.execute(_coding_input())

        assert result.is_valid is True
        assert result.errors == ()

    async def test_warns_when_no_narrative_content_provided(self) -> None:
        use_case = ValidateClinicalContextUseCase()

        result = await use_case.execute(_coding_input())

        assert any("hpi" in warning.lower() for warning in result.warnings)

    async def test_no_narrative_warning_when_history_of_present_illness_given(self) -> None:
        use_case = ValidateClinicalContextUseCase()

        result = await use_case.execute(
            _coding_input(history_of_present_illness="Gradual onset over 2 days")
        )

        assert not any("hpi" in warning.lower() for warning in result.warnings)

    async def test_no_narrative_warning_when_symptoms_given(self) -> None:
        use_case = ValidateClinicalContextUseCase()

        result = await use_case.execute(_coding_input(symptoms=("sore throat",)))

        assert not any("hpi" in warning.lower() for warning in result.warnings)

    async def test_warns_when_no_clinical_summary_provided(self) -> None:
        use_case = ValidateClinicalContextUseCase()

        result = await use_case.execute(_coding_input())

        assert any("assessment" in warning.lower() for warning in result.warnings)

    async def test_no_clinical_summary_warning_when_clinical_note_given(self) -> None:
        use_case = ValidateClinicalContextUseCase()

        result = await use_case.execute(_coding_input(clinical_note="Full clinical note text"))

        assert not any("assessment" in warning.lower() for warning in result.warnings)

    async def test_no_clinical_summary_warning_when_soap_note_given(self) -> None:
        use_case = ValidateClinicalContextUseCase()

        result = await use_case.execute(_coding_input(soap_note="Full SOAP note text"))

        assert not any("assessment" in warning.lower() for warning in result.warnings)

    async def test_warns_when_no_existing_diagnoses_provided(self) -> None:
        use_case = ValidateClinicalContextUseCase()

        result = await use_case.execute(_coding_input())

        assert any("existing diagnoses" in warning.lower() for warning in result.warnings)

    async def test_no_existing_diagnoses_warning_when_provided(self) -> None:
        use_case = ValidateClinicalContextUseCase()

        result = await use_case.execute(_coding_input(existing_diagnoses=("asthma",)))

        assert not any("existing diagnoses" in warning.lower() for warning in result.warnings)

    async def test_no_warnings_when_fully_populated(self) -> None:
        use_case = ValidateClinicalContextUseCase()

        result = await use_case.execute(
            _coding_input(
                history_of_present_illness="Gradual onset",
                assessment="Acute pharyngitis",
                existing_diagnoses=("seasonal allergies",),
            )
        )

        assert result.warnings == ()

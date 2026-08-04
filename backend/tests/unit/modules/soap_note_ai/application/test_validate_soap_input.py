"""Unit tests for `ValidateSOAPInputUseCase`."""

from uuid import uuid4

from app.modules.soap_note_ai.application.use_cases.validate_soap_input import (
    ValidateSOAPInputUseCase,
)
from app.modules.soap_note_ai.domain.enums import SOAPStyle
from app.modules.soap_note_ai.domain.value_objects import SOAPEncounterInput


def _encounter(**overrides: object) -> SOAPEncounterInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Headache",
        "soap_style": SOAPStyle.STANDARD,
    }
    defaults.update(overrides)
    return SOAPEncounterInput(**defaults)  # type: ignore[arg-type]


class TestValidateSOAPInputUseCase:
    async def test_is_always_valid(self) -> None:
        use_case = ValidateSOAPInputUseCase()

        result = await use_case.execute(_encounter())

        assert result.is_valid is True
        assert result.errors == ()

    async def test_warns_when_no_subjective_content_provided(self) -> None:
        use_case = ValidateSOAPInputUseCase()

        result = await use_case.execute(_encounter())

        assert any("subjective" in warning.lower() for warning in result.warnings)

    async def test_no_subjective_warning_when_history_of_present_illness_given(self) -> None:
        use_case = ValidateSOAPInputUseCase()

        result = await use_case.execute(
            _encounter(history_of_present_illness="Gradual onset over 2 days")
        )

        assert not any("subjective" in warning.lower() for warning in result.warnings)

    async def test_no_subjective_warning_when_symptoms_given(self) -> None:
        use_case = ValidateSOAPInputUseCase()

        result = await use_case.execute(_encounter(symptoms=("throbbing",)))

        assert not any("subjective" in warning.lower() for warning in result.warnings)

    async def test_warns_when_no_objective_content_provided(self) -> None:
        use_case = ValidateSOAPInputUseCase()

        result = await use_case.execute(_encounter())

        assert any("physical examination" in warning.lower() for warning in result.warnings)

    async def test_no_objective_warning_when_vitals_given(self) -> None:
        use_case = ValidateSOAPInputUseCase()

        result = await use_case.execute(_encounter(vitals={"BP": "120/80"}))

        assert not any("physical examination" in warning.lower() for warning in result.warnings)

    async def test_warns_when_no_assessment_or_diagnoses_provided(self) -> None:
        use_case = ValidateSOAPInputUseCase()

        result = await use_case.execute(_encounter())

        assert any("assessment" in warning.lower() for warning in result.warnings)

    async def test_no_assessment_warning_when_diagnoses_given(self) -> None:
        use_case = ValidateSOAPInputUseCase()

        result = await use_case.execute(_encounter(diagnoses=("tension headache",)))

        assert not any("assessment" in warning.lower() for warning in result.warnings)

    async def test_warns_when_no_plan_provided(self) -> None:
        use_case = ValidateSOAPInputUseCase()

        result = await use_case.execute(_encounter())

        assert any("plan" in warning.lower() for warning in result.warnings)

    async def test_no_warnings_when_fully_populated(self) -> None:
        use_case = ValidateSOAPInputUseCase()

        result = await use_case.execute(
            _encounter(
                history_of_present_illness="Gradual onset",
                physical_examination="Unremarkable",
                assessment="Tension headache",
                plan="OTC analgesics",
            )
        )

        assert result.warnings == ()

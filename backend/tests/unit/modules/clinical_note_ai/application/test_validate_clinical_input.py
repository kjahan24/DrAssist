"""Unit tests for `ValidateClinicalInputUseCase`."""

from uuid import uuid4

from app.modules.clinical_note_ai.application.use_cases.validate_clinical_input import (
    ValidateClinicalInputUseCase,
)
from app.modules.clinical_note_ai.domain.enums import NoteStyle
from app.modules.clinical_note_ai.domain.value_objects import ClinicalEncounterInput


def _encounter(**overrides: object) -> ClinicalEncounterInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Headache",
        "note_style": NoteStyle.CONCISE,
    }
    defaults.update(overrides)
    return ClinicalEncounterInput(**defaults)  # type: ignore[arg-type]


class TestValidateClinicalInputUseCase:
    async def test_is_always_valid_for_a_structurally_valid_encounter(self) -> None:
        use_case = ValidateClinicalInputUseCase()

        result = await use_case.execute(_encounter())

        assert result.is_valid is True
        assert result.errors == ()

    async def test_warns_when_no_history_symptoms_or_observations_given(self) -> None:
        use_case = ValidateClinicalInputUseCase()

        result = await use_case.execute(_encounter())

        assert any("history of present illness" in warning for warning in result.warnings)

    async def test_no_history_warning_when_symptoms_are_given(self) -> None:
        use_case = ValidateClinicalInputUseCase()

        result = await use_case.execute(_encounter(symptoms=("throbbing pain",)))

        assert not any("history of present illness" in warning for warning in result.warnings)

    async def test_warns_when_no_physical_examination_given(self) -> None:
        use_case = ValidateClinicalInputUseCase()

        result = await use_case.execute(_encounter())

        assert any("physical examination" in warning for warning in result.warnings)

    async def test_warns_when_no_assessment_or_diagnoses_given(self) -> None:
        use_case = ValidateClinicalInputUseCase()

        result = await use_case.execute(_encounter())

        assert any("assessment" in warning for warning in result.warnings)

    async def test_no_assessment_warning_when_diagnoses_are_given(self) -> None:
        use_case = ValidateClinicalInputUseCase()

        result = await use_case.execute(_encounter(diagnoses=("tension headache",)))

        assert not any("assessment" in warning for warning in result.warnings)

    async def test_warns_when_no_plan_given(self) -> None:
        use_case = ValidateClinicalInputUseCase()

        result = await use_case.execute(_encounter())

        assert any("plan" in warning for warning in result.warnings)

    async def test_no_warnings_for_a_fully_populated_encounter(self) -> None:
        use_case = ValidateClinicalInputUseCase()

        result = await use_case.execute(
            _encounter(
                history_of_present_illness="Gradual onset",
                physical_examination="Unremarkable",
                assessment="Tension headache",
                plan="OTC analgesics",
            )
        )

        assert result.warnings == ()

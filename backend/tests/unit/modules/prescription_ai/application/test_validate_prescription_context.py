"""Unit tests for `ValidatePrescriptionContextUseCase`."""

from uuid import uuid4

from app.modules.prescription_ai.application.use_cases.validate_prescription_context import (
    ValidatePrescriptionContextUseCase,
)
from app.modules.prescription_ai.domain.enums import PatientSex, PregnancyStatus, PrescribingSetting
from app.modules.prescription_ai.domain.value_objects import PrescriptionContextInput


def _context(**overrides: object) -> PrescriptionContextInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Sore throat",
        "prescribing_setting": PrescribingSetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return PrescriptionContextInput(**defaults)  # type: ignore[arg-type]


class TestValidatePrescriptionContextUseCase:
    async def test_is_always_valid(self) -> None:
        use_case = ValidatePrescriptionContextUseCase()

        result = await use_case.execute(_context())

        assert result.is_valid is True
        assert result.errors == ()

    async def test_warns_when_no_narrative_content_provided(self) -> None:
        use_case = ValidatePrescriptionContextUseCase()

        result = await use_case.execute(_context())

        assert any("hpi" in warning.lower() for warning in result.warnings)

    async def test_no_narrative_warning_when_symptoms_given(self) -> None:
        use_case = ValidatePrescriptionContextUseCase()

        result = await use_case.execute(_context(symptoms=("sore throat",)))

        assert not any("hpi" in warning.lower() for warning in result.warnings)

    async def test_warns_when_no_clinical_summary_provided(self) -> None:
        use_case = ValidatePrescriptionContextUseCase()

        result = await use_case.execute(_context())

        assert any("assessment" in warning.lower() for warning in result.warnings)

    async def test_no_clinical_summary_warning_when_assessment_given(self) -> None:
        use_case = ValidatePrescriptionContextUseCase()

        result = await use_case.execute(_context(assessment="Acute pharyngitis"))

        assert not any("assessment" in warning.lower() for warning in result.warnings)

    async def test_warns_when_no_allergies_provided(self) -> None:
        use_case = ValidatePrescriptionContextUseCase()

        result = await use_case.execute(_context())

        assert any("allergy" in warning.lower() for warning in result.warnings)

    async def test_no_allergy_warning_when_allergies_given(self) -> None:
        use_case = ValidatePrescriptionContextUseCase()

        result = await use_case.execute(_context(allergies=("penicillin",)))

        assert not any("allergy information" in warning.lower() for warning in result.warnings)

    async def test_warns_when_no_existing_medications_provided(self) -> None:
        use_case = ValidatePrescriptionContextUseCase()

        result = await use_case.execute(_context())

        assert any("existing medications" in warning.lower() for warning in result.warnings)

    async def test_no_existing_medications_warning_when_provided(self) -> None:
        use_case = ValidatePrescriptionContextUseCase()

        result = await use_case.execute(_context(existing_medications=("lisinopril",)))

        assert not any("existing medications" in warning.lower() for warning in result.warnings)

    async def test_warns_when_pediatric_setting_missing_weight(self) -> None:
        use_case = ValidatePrescriptionContextUseCase()

        result = await use_case.execute(_context(prescribing_setting=PrescribingSetting.PEDIATRIC))

        assert any("weight" in warning.lower() for warning in result.warnings)

    async def test_no_weight_warning_when_pediatric_setting_has_weight(self) -> None:
        use_case = ValidatePrescriptionContextUseCase()

        result = await use_case.execute(
            _context(prescribing_setting=PrescribingSetting.PEDIATRIC, weight_kg=22.0)
        )

        assert not any("weight" in warning.lower() for warning in result.warnings)

    async def test_no_weight_warning_for_non_pediatric_setting(self) -> None:
        use_case = ValidatePrescriptionContextUseCase()

        result = await use_case.execute(_context(prescribing_setting=PrescribingSetting.OUTPATIENT))

        assert not any("weight" in warning.lower() for warning in result.warnings)

    async def test_warns_when_female_patient_missing_pregnancy_status(self) -> None:
        use_case = ValidatePrescriptionContextUseCase()

        result = await use_case.execute(_context(patient_sex=PatientSex.FEMALE))

        assert any("pregnancy" in warning.lower() for warning in result.warnings)

    async def test_no_pregnancy_warning_when_status_provided(self) -> None:
        use_case = ValidatePrescriptionContextUseCase()

        result = await use_case.execute(
            _context(patient_sex=PatientSex.FEMALE, pregnancy_status=PregnancyStatus.NOT_PREGNANT)
        )

        assert not any("pregnancy" in warning.lower() for warning in result.warnings)

    async def test_no_pregnancy_warning_for_male_patient(self) -> None:
        use_case = ValidatePrescriptionContextUseCase()

        result = await use_case.execute(_context(patient_sex=PatientSex.MALE))

        assert not any("pregnancy" in warning.lower() for warning in result.warnings)

    async def test_no_warnings_when_fully_populated(self) -> None:
        use_case = ValidatePrescriptionContextUseCase()

        result = await use_case.execute(
            _context(
                history_of_present_illness="Gradual onset",
                assessment="Acute pharyngitis",
                allergies=("none known",),
                existing_medications=("none",),
                patient_sex=PatientSex.MALE,
            )
        )

        assert result.warnings == ()

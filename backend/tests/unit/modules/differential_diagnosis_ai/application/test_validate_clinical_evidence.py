"""Unit tests for `ValidateClinicalEvidenceUseCase`."""

from uuid import uuid4

from app.modules.differential_diagnosis_ai.application.services.clinical_reasoning_service import (
    ClinicalReasoningService,
)
from app.modules.differential_diagnosis_ai.application.use_cases.validate_clinical_evidence import (
    ValidateClinicalEvidenceUseCase,
)
from app.modules.differential_diagnosis_ai.domain.enums import ClinicalSetting
from app.modules.differential_diagnosis_ai.domain.value_objects import DifferentialDiagnosisInput
from tests.unit.modules.differential_diagnosis_ai.application.fakes import (
    FakeClinicalReasoningPort,
)


def _evidence(**overrides: object) -> DifferentialDiagnosisInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Chest pain",
        "clinical_setting": ClinicalSetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return DifferentialDiagnosisInput(**defaults)  # type: ignore[arg-type]


class TestValidateClinicalEvidenceUseCase:
    async def test_is_always_valid(self) -> None:
        use_case = ValidateClinicalEvidenceUseCase(
            reasoning_service=ClinicalReasoningService(reasoning=FakeClinicalReasoningPort())
        )

        result = await use_case.execute(_evidence())

        assert result.is_valid is True
        assert result.errors == ()

    async def test_includes_missing_information_warnings_from_the_reasoning_service(self) -> None:
        reasoning_port = FakeClinicalReasoningPort(missing_information=("no labs provided",))
        use_case = ValidateClinicalEvidenceUseCase(
            reasoning_service=ClinicalReasoningService(reasoning=reasoning_port)
        )

        result = await use_case.execute(_evidence())

        assert "no labs provided" in result.warnings

    async def test_warns_when_no_allergies_provided(self) -> None:
        use_case = ValidateClinicalEvidenceUseCase(
            reasoning_service=ClinicalReasoningService(reasoning=FakeClinicalReasoningPort())
        )

        result = await use_case.execute(_evidence())

        assert any("allergy" in warning.lower() for warning in result.warnings)

    async def test_no_allergy_warning_when_allergies_given(self) -> None:
        use_case = ValidateClinicalEvidenceUseCase(
            reasoning_service=ClinicalReasoningService(reasoning=FakeClinicalReasoningPort())
        )

        result = await use_case.execute(_evidence(allergies=("penicillin",)))

        assert not any("allergy" in warning.lower() for warning in result.warnings)

    async def test_warns_when_no_medical_conditions_provided(self) -> None:
        use_case = ValidateClinicalEvidenceUseCase(
            reasoning_service=ClinicalReasoningService(reasoning=FakeClinicalReasoningPort())
        )

        result = await use_case.execute(_evidence())

        assert any("medical conditions" in warning.lower() for warning in result.warnings)

    async def test_no_medical_conditions_warning_when_provided(self) -> None:
        use_case = ValidateClinicalEvidenceUseCase(
            reasoning_service=ClinicalReasoningService(reasoning=FakeClinicalReasoningPort())
        )

        result = await use_case.execute(_evidence(medical_conditions=("hypertension",)))

        assert not any("medical conditions" in warning.lower() for warning in result.warnings)

    async def test_calls_reasoning_service_with_the_evidence(self) -> None:
        reasoning_port = FakeClinicalReasoningPort()
        use_case = ValidateClinicalEvidenceUseCase(
            reasoning_service=ClinicalReasoningService(reasoning=reasoning_port)
        )
        evidence = _evidence()

        await use_case.execute(evidence)

        assert reasoning_port.missing_information_calls == [evidence]

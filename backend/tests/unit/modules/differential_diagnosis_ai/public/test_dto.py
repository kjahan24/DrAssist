"""Unit tests confirming `public/dto.py` re-exports the correct shapes
without redefining them."""

from app.modules.differential_diagnosis_ai.application.dto import (
    GeneratedDifferentialDiagnosis as ApplicationGeneratedDifferentialDiagnosis,
)
from app.modules.differential_diagnosis_ai.domain.enums import (
    ClinicalSetting as DomainClinicalSetting,
)
from app.modules.differential_diagnosis_ai.domain.enums import (
    DifferentialOutputFormat as DomainFormat,
)
from app.modules.differential_diagnosis_ai.domain.enums import PatientSex as DomainPatientSex
from app.modules.differential_diagnosis_ai.domain.value_objects import (
    DifferentialDiagnosisCandidate as DomainDifferentialDiagnosisCandidate,
)
from app.modules.differential_diagnosis_ai.domain.value_objects import (
    DifferentialDiagnosisInput as DomainDifferentialDiagnosisInput,
)
from app.modules.differential_diagnosis_ai.public.dto import (
    ClinicalSetting,
    DifferentialDiagnosisCandidate,
    DifferentialDiagnosisInput,
    DifferentialOutputFormat,
    GeneratedDifferentialDiagnosis,
    PatientSex,
)


class TestPublicDtoReExports:
    def test_differential_diagnosis_input_is_the_domain_type(self) -> None:
        assert DifferentialDiagnosisInput is DomainDifferentialDiagnosisInput

    def test_differential_diagnosis_candidate_is_the_domain_type(self) -> None:
        assert DifferentialDiagnosisCandidate is DomainDifferentialDiagnosisCandidate

    def test_generated_differential_diagnosis_is_the_application_type(self) -> None:
        assert GeneratedDifferentialDiagnosis is ApplicationGeneratedDifferentialDiagnosis

    def test_clinical_setting_is_the_domain_type(self) -> None:
        assert ClinicalSetting is DomainClinicalSetting

    def test_differential_output_format_is_the_domain_type(self) -> None:
        assert DifferentialOutputFormat is DomainFormat

    def test_patient_sex_is_the_domain_type(self) -> None:
        assert PatientSex is DomainPatientSex

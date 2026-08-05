"""Unit tests confirming `public/dto.py` re-exports the correct shapes
without redefining them."""

from app.modules.patient_education_ai.application.dto import (
    GeneratedPatientEducation as ApplicationGeneratedPatientEducation,
)
from app.modules.patient_education_ai.domain.enums import (
    PatientEducationOutputFormat as DomainPatientEducationOutputFormat,
)
from app.modules.patient_education_ai.domain.enums import (
    PatientEducationSetting as DomainPatientEducationSetting,
)
from app.modules.patient_education_ai.domain.value_objects import (
    PatientEducationInput as DomainPatientEducationInput,
)
from app.modules.patient_education_ai.domain.value_objects import (
    PatientEducationResult as DomainPatientEducationResult,
)
from app.modules.patient_education_ai.public.dto import (
    GeneratedPatientEducation,
    PatientEducationInput,
    PatientEducationOutputFormat,
    PatientEducationResult,
    PatientEducationSetting,
)


class TestPublicDtoReExports:
    def test_patient_education_input_is_the_domain_type(self) -> None:
        assert PatientEducationInput is DomainPatientEducationInput

    def test_patient_education_result_is_the_domain_type(self) -> None:
        assert PatientEducationResult is DomainPatientEducationResult

    def test_generated_patient_education_is_the_application_type(self) -> None:
        assert GeneratedPatientEducation is ApplicationGeneratedPatientEducation

    def test_patient_education_setting_is_the_domain_type(self) -> None:
        assert PatientEducationSetting is DomainPatientEducationSetting

    def test_patient_education_output_format_is_the_domain_type(self) -> None:
        assert PatientEducationOutputFormat is DomainPatientEducationOutputFormat

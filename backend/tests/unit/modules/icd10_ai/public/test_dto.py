"""Unit tests confirming `public/dto.py` re-exports the correct shapes
without redefining them."""

from app.modules.icd10_ai.application.dto import (
    GeneratedICD10Suggestions as ApplicationGeneratedICD10Suggestions,
)
from app.modules.icd10_ai.domain.enums import CodingSetting as DomainCodingSetting
from app.modules.icd10_ai.domain.enums import ICD10OutputFormat as DomainFormat
from app.modules.icd10_ai.domain.enums import PatientSex as DomainPatientSex
from app.modules.icd10_ai.domain.value_objects import ICD10CodingInput as DomainICD10CodingInput
from app.modules.icd10_ai.domain.value_objects import ICD10Suggestion as DomainICD10Suggestion
from app.modules.icd10_ai.public.dto import (
    CodingSetting,
    GeneratedICD10Suggestions,
    ICD10CodingInput,
    ICD10OutputFormat,
    ICD10Suggestion,
    PatientSex,
)


class TestPublicDtoReExports:
    def test_icd10_coding_input_is_the_domain_type(self) -> None:
        assert ICD10CodingInput is DomainICD10CodingInput

    def test_icd10_suggestion_is_the_domain_type(self) -> None:
        assert ICD10Suggestion is DomainICD10Suggestion

    def test_generated_icd10_suggestions_is_the_application_type(self) -> None:
        assert GeneratedICD10Suggestions is ApplicationGeneratedICD10Suggestions

    def test_coding_setting_is_the_domain_type(self) -> None:
        assert CodingSetting is DomainCodingSetting

    def test_icd10_output_format_is_the_domain_type(self) -> None:
        assert ICD10OutputFormat is DomainFormat

    def test_patient_sex_is_the_domain_type(self) -> None:
        assert PatientSex is DomainPatientSex

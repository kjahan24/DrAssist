"""Unit tests confirming `public/dto.py` re-exports the correct shapes
without redefining them."""

from app.modules.radiology_interpretation_ai.application.dto import (
    GeneratedRadiologyInterpretation as ApplicationGeneratedRadiologyInterpretation,
)
from app.modules.radiology_interpretation_ai.domain.enums import (
    PatientSex as DomainPatientSex,
)
from app.modules.radiology_interpretation_ai.domain.enums import (
    RadiologyExaminationType as DomainRadiologyExaminationType,
)
from app.modules.radiology_interpretation_ai.domain.enums import (
    RadiologyFindingCategory as DomainRadiologyFindingCategory,
)
from app.modules.radiology_interpretation_ai.domain.value_objects import (
    RadiologyFinding as DomainRadiologyFinding,
)
from app.modules.radiology_interpretation_ai.domain.value_objects import (
    RadiologyInterpretationInput as DomainRadiologyInterpretationInput,
)
from app.modules.radiology_interpretation_ai.public.dto import (
    GeneratedRadiologyInterpretation,
    PatientSex,
    RadiologyExaminationType,
    RadiologyFinding,
    RadiologyFindingCategory,
    RadiologyInterpretationInput,
)


class TestPublicDtoReExports:
    def test_radiology_interpretation_input_is_the_domain_type(self) -> None:
        assert RadiologyInterpretationInput is DomainRadiologyInterpretationInput

    def test_radiology_finding_is_the_domain_type(self) -> None:
        assert RadiologyFinding is DomainRadiologyFinding

    def test_generated_radiology_interpretation_is_the_application_type(self) -> None:
        assert GeneratedRadiologyInterpretation is ApplicationGeneratedRadiologyInterpretation

    def test_radiology_examination_type_is_the_domain_type(self) -> None:
        assert RadiologyExaminationType is DomainRadiologyExaminationType

    def test_radiology_finding_category_is_the_domain_type(self) -> None:
        assert RadiologyFindingCategory is DomainRadiologyFindingCategory

    def test_patient_sex_is_the_domain_type(self) -> None:
        assert PatientSex is DomainPatientSex

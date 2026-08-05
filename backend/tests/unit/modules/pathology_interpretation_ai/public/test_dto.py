"""Unit tests confirming `public/dto.py` re-exports the correct shapes
without redefining them."""

from app.modules.pathology_interpretation_ai.application.dto import (
    GeneratedPathologyInterpretation as ApplicationGeneratedPathologyInterpretation,
)
from app.modules.pathology_interpretation_ai.domain.enums import (
    PathologyExaminationType as DomainPathologyExaminationType,
)
from app.modules.pathology_interpretation_ai.domain.enums import (
    PathologyFindingCategory as DomainPathologyFindingCategory,
)
from app.modules.pathology_interpretation_ai.domain.enums import PatientSex as DomainPatientSex
from app.modules.pathology_interpretation_ai.domain.value_objects import (
    PathologyFinding as DomainPathologyFinding,
)
from app.modules.pathology_interpretation_ai.domain.value_objects import (
    PathologyInterpretationInput as DomainPathologyInterpretationInput,
)
from app.modules.pathology_interpretation_ai.public.dto import (
    GeneratedPathologyInterpretation,
    PathologyExaminationType,
    PathologyFinding,
    PathologyFindingCategory,
    PathologyInterpretationInput,
    PatientSex,
)


class TestPublicDtoReExports:
    def test_pathology_interpretation_input_is_the_domain_type(self) -> None:
        assert PathologyInterpretationInput is DomainPathologyInterpretationInput

    def test_pathology_finding_is_the_domain_type(self) -> None:
        assert PathologyFinding is DomainPathologyFinding

    def test_generated_pathology_interpretation_is_the_application_type(self) -> None:
        assert GeneratedPathologyInterpretation is ApplicationGeneratedPathologyInterpretation

    def test_pathology_examination_type_is_the_domain_type(self) -> None:
        assert PathologyExaminationType is DomainPathologyExaminationType

    def test_pathology_finding_category_is_the_domain_type(self) -> None:
        assert PathologyFindingCategory is DomainPathologyFindingCategory

    def test_patient_sex_is_the_domain_type(self) -> None:
        assert PatientSex is DomainPatientSex

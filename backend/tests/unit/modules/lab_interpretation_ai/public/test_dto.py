"""Unit tests confirming `public/dto.py` re-exports the correct shapes
without redefining them."""

from app.modules.lab_interpretation_ai.application.dto import (
    GeneratedLabInterpretation as ApplicationGeneratedLabInterpretation,
)
from app.modules.lab_interpretation_ai.domain.enums import (
    LabFindingFlag as DomainLabFindingFlag,
)
from app.modules.lab_interpretation_ai.domain.enums import PatientSex as DomainPatientSex
from app.modules.lab_interpretation_ai.domain.value_objects import (
    LabInterpretationInput as DomainLabInterpretationInput,
)
from app.modules.lab_interpretation_ai.domain.value_objects import LabValue as DomainLabValue
from app.modules.lab_interpretation_ai.public.dto import (
    GeneratedLabInterpretation,
    LabFindingFlag,
    LabInterpretationInput,
    LabValue,
    PatientSex,
)


class TestPublicDtoReExports:
    def test_lab_interpretation_input_is_the_domain_type(self) -> None:
        assert LabInterpretationInput is DomainLabInterpretationInput

    def test_lab_value_is_the_domain_type(self) -> None:
        assert LabValue is DomainLabValue

    def test_generated_lab_interpretation_is_the_application_type(self) -> None:
        assert GeneratedLabInterpretation is ApplicationGeneratedLabInterpretation

    def test_lab_finding_flag_is_the_domain_type(self) -> None:
        assert LabFindingFlag is DomainLabFindingFlag

    def test_patient_sex_is_the_domain_type(self) -> None:
        assert PatientSex is DomainPatientSex

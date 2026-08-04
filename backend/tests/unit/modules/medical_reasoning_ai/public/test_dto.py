"""Unit tests confirming `public/dto.py` re-exports the correct shapes
without redefining them."""

from app.modules.medical_reasoning_ai.application.dto import (
    GeneratedMedicalReasoning as ApplicationGeneratedMedicalReasoning,
)
from app.modules.medical_reasoning_ai.domain.enums import (
    EvidencePolarity as DomainEvidencePolarity,
)
from app.modules.medical_reasoning_ai.domain.enums import PatientSex as DomainPatientSex
from app.modules.medical_reasoning_ai.domain.enums import ReasoningSetting as DomainReasoningSetting
from app.modules.medical_reasoning_ai.domain.value_objects import EvidenceItem as DomainEvidenceItem
from app.modules.medical_reasoning_ai.domain.value_objects import (
    MedicalReasoningInput as DomainMedicalReasoningInput,
)
from app.modules.medical_reasoning_ai.public.dto import (
    EvidenceItem,
    EvidencePolarity,
    GeneratedMedicalReasoning,
    MedicalReasoningInput,
    PatientSex,
    ReasoningSetting,
)


class TestPublicDtoReExports:
    def test_medical_reasoning_input_is_the_domain_type(self) -> None:
        assert MedicalReasoningInput is DomainMedicalReasoningInput

    def test_evidence_item_is_the_domain_type(self) -> None:
        assert EvidenceItem is DomainEvidenceItem

    def test_generated_medical_reasoning_is_the_application_type(self) -> None:
        assert GeneratedMedicalReasoning is ApplicationGeneratedMedicalReasoning

    def test_reasoning_setting_is_the_domain_type(self) -> None:
        assert ReasoningSetting is DomainReasoningSetting

    def test_evidence_polarity_is_the_domain_type(self) -> None:
        assert EvidencePolarity is DomainEvidencePolarity

    def test_patient_sex_is_the_domain_type(self) -> None:
        assert PatientSex is DomainPatientSex

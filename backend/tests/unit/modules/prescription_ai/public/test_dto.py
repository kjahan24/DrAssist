"""Unit tests confirming `public/dto.py` re-exports the correct shapes
without redefining them."""

from app.modules.prescription_ai.application.dto import (
    GeneratedPrescriptionSuggestions as ApplicationGeneratedPrescriptionSuggestions,
)
from app.modules.prescription_ai.domain.enums import (
    AdministrationRoute as DomainAdministrationRoute,
)
from app.modules.prescription_ai.domain.enums import PatientSex as DomainPatientSex
from app.modules.prescription_ai.domain.enums import PrescribingSetting as DomainPrescribingSetting
from app.modules.prescription_ai.domain.value_objects import (
    MedicationSuggestion as DomainMedicationSuggestion,
)
from app.modules.prescription_ai.domain.value_objects import (
    PrescriptionContextInput as DomainPrescriptionContextInput,
)
from app.modules.prescription_ai.public.dto import (
    AdministrationRoute,
    GeneratedPrescriptionSuggestions,
    MedicationSuggestion,
    PatientSex,
    PrescribingSetting,
    PrescriptionContextInput,
)


class TestPublicDtoReExports:
    def test_prescription_context_input_is_the_domain_type(self) -> None:
        assert PrescriptionContextInput is DomainPrescriptionContextInput

    def test_medication_suggestion_is_the_domain_type(self) -> None:
        assert MedicationSuggestion is DomainMedicationSuggestion

    def test_generated_prescription_suggestions_is_the_application_type(self) -> None:
        assert GeneratedPrescriptionSuggestions is ApplicationGeneratedPrescriptionSuggestions

    def test_prescribing_setting_is_the_domain_type(self) -> None:
        assert PrescribingSetting is DomainPrescribingSetting

    def test_administration_route_is_the_domain_type(self) -> None:
        assert AdministrationRoute is DomainAdministrationRoute

    def test_patient_sex_is_the_domain_type(self) -> None:
        assert PatientSex is DomainPatientSex

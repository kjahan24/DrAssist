"""Unit tests for the AI Prescription Assistance module's domain value
objects."""

from uuid import uuid4

import pytest

from app.modules.prescription_ai.domain.enums import (
    AdministrationRoute,
    GenerationStatus,
    PatientSex,
    PregnancyStatus,
    PrescribingSetting,
    PrescriptionOutputFormat,
    SafetyFindingCategory,
    SafetySeverity,
)
from app.modules.prescription_ai.domain.exceptions import InvalidPrescriptionContextError
from app.modules.prescription_ai.domain.value_objects import (
    GenerationSession,
    MedicationSafetyFinding,
    MedicationSuggestion,
    PrescriptionContextInput,
    PrescriptionStreamChunk,
    PrescriptionSuggestionSet,
    PrescriptionTemplateSet,
)


def _context(**overrides: object) -> PrescriptionContextInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Sore throat",
        "prescribing_setting": PrescribingSetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return PrescriptionContextInput(**defaults)  # type: ignore[arg-type]


class TestPrescriptionContextInput:
    def test_constructs_with_required_fields_only(self) -> None:
        context = _context()
        assert context.chief_complaint == "Sore throat"
        assert context.language == "en"
        assert context.visit_id is None
        assert context.symptoms == ()
        assert context.existing_medications == ()
        assert context.allergies == ()
        assert context.patient_age is None
        assert context.patient_sex is None
        assert context.pregnancy_status is None
        assert context.weight_kg is None
        assert context.output_format is PrescriptionOutputFormat.JSON

    def test_accepts_the_full_set_of_optional_fields(self) -> None:
        visit_id = uuid4()
        context = _context(
            visit_id=visit_id,
            history_of_present_illness="Gradual onset over 2 days",
            symptoms=("sore throat", "fever"),
            review_of_systems="Negative except as noted",
            physical_examination="Erythematous pharynx",
            vitals={"BP": "120/80"},
            assessment="Acute pharyngitis",
            plan="Supportive care",
            clinical_note="Full clinical note text",
            soap_note="Full SOAP note text",
            icd10_suggestions=("J06.9",),
            existing_medications=("lisinopril",),
            allergies=("penicillin",),
            medical_conditions=("hypertension",),
            laboratory_results=("WBC: 11.2",),
            patient_age=34,
            patient_sex=PatientSex.FEMALE,
            pregnancy_status=PregnancyStatus.NOT_PREGNANT,
            weight_kg=68.5,
            visit_type="Outpatient",
            language="es",
            prescribing_setting=PrescribingSetting.EMERGENCY,
            output_format=PrescriptionOutputFormat.MARKDOWN,
        )
        assert context.visit_id == visit_id
        assert context.patient_age == 34
        assert context.patient_sex is PatientSex.FEMALE
        assert context.pregnancy_status is PregnancyStatus.NOT_PREGNANT
        assert context.weight_kg == 68.5
        assert context.prescribing_setting is PrescribingSetting.EMERGENCY
        assert context.output_format is PrescriptionOutputFormat.MARKDOWN

    @pytest.mark.parametrize("chief_complaint", ["", "   "])
    def test_rejects_blank_chief_complaint(self, chief_complaint: str) -> None:
        with pytest.raises(InvalidPrescriptionContextError):
            _context(chief_complaint=chief_complaint)

    @pytest.mark.parametrize("language", ["", "   "])
    def test_rejects_blank_language(self, language: str) -> None:
        with pytest.raises(InvalidPrescriptionContextError):
            _context(language=language)

    @pytest.mark.parametrize("patient_age", [-1, 151, -100])
    def test_rejects_implausible_patient_age(self, patient_age: int) -> None:
        with pytest.raises(InvalidPrescriptionContextError):
            _context(patient_age=patient_age)

    @pytest.mark.parametrize("patient_age", [0, 1, 150])
    def test_accepts_boundary_valid_ages(self, patient_age: int) -> None:
        context = _context(patient_age=patient_age)
        assert context.patient_age == patient_age

    @pytest.mark.parametrize("weight_kg", [0.0, -1.0, 500.1, 1000.0])
    def test_rejects_implausible_weight(self, weight_kg: float) -> None:
        with pytest.raises(InvalidPrescriptionContextError):
            _context(weight_kg=weight_kg)

    @pytest.mark.parametrize("weight_kg", [0.1, 68.5, 500.0])
    def test_accepts_boundary_valid_weights(self, weight_kg: float) -> None:
        context = _context(weight_kg=weight_kg)
        assert context.weight_kg == weight_kg

    def test_equality_is_by_value(self) -> None:
        organization_id = uuid4()
        patient_id = uuid4()
        a = _context(organization_id=organization_id, patient_id=patient_id)
        b = _context(organization_id=organization_id, patient_id=patient_id)
        assert a == b


class TestMedicationSuggestion:
    def _medication(self, **overrides: object) -> MedicationSuggestion:
        defaults: dict[str, object] = {
            "generic_name": "amoxicillin",
            "brand_name": None,
            "strength": "500mg",
            "dosage": "1 capsule",
            "route": AdministrationRoute.ORAL,
            "frequency": "three times daily",
            "duration": "7 days",
            "quantity": "21 capsules",
            "is_prn": False,
            "clinical_indication": "Acute pharyngitis",
            "monitoring_advice": "Watch for rash",
            "patient_instructions": "Take with food",
            "confidence_score": 0.85,
            "clinical_reasoning": "First-line for bacterial pharyngitis",
        }
        defaults.update(overrides)
        return MedicationSuggestion(**defaults)  # type: ignore[arg-type]

    def test_constructs_with_all_fields(self) -> None:
        medication = self._medication()
        assert medication.generic_name == "amoxicillin"
        assert medication.route is AdministrationRoute.ORAL
        assert medication.is_prn is False

    def test_accepts_a_null_brand_name(self) -> None:
        medication = self._medication(brand_name=None)
        assert medication.brand_name is None

    def test_accepts_a_null_confidence_score(self) -> None:
        medication = self._medication(confidence_score=None)
        assert medication.confidence_score is None

    def test_equality_is_by_value(self) -> None:
        a = self._medication()
        b = self._medication()
        assert a == b


class TestMedicationSafetyFinding:
    def test_constructs_with_default_empty_affected_medications(self) -> None:
        finding = MedicationSafetyFinding(
            category=SafetyFindingCategory.DRUG_INTERACTION,
            severity=SafetySeverity.HIGH,
            description="Increased bleeding risk.",
        )
        assert finding.affected_medications == ()

    def test_accepts_affected_medications(self) -> None:
        finding = MedicationSafetyFinding(
            category=SafetyFindingCategory.ALLERGY_CONFLICT,
            severity=SafetySeverity.CRITICAL,
            description="Cross-reactive with penicillin allergy.",
            affected_medications=("amoxicillin",),
        )
        assert finding.affected_medications == ("amoxicillin",)


class TestPrescriptionSuggestionSet:
    def _suggestion_set(self, **overrides: object) -> PrescriptionSuggestionSet:
        defaults: dict[str, object] = {
            "medications": (
                MedicationSuggestion(
                    generic_name="amoxicillin",
                    brand_name=None,
                    strength="500mg",
                    dosage="1 capsule",
                    route=AdministrationRoute.ORAL,
                    frequency="three times daily",
                    duration="7 days",
                    quantity="21 capsules",
                    is_prn=False,
                    clinical_indication="Acute pharyngitis",
                    monitoring_advice="Watch for rash",
                    patient_instructions="Take with food",
                    confidence_score=0.85,
                    clinical_reasoning="First-line for bacterial pharyngitis",
                ),
            ),
            "safety_findings": (),
            "monitoring_recommendations": (),
            "follow_up_recommendations": (),
            "raw_text": '{"medications": []}',
            "output_format": PrescriptionOutputFormat.JSON,
        }
        defaults.update(overrides)
        return PrescriptionSuggestionSet(**defaults)  # type: ignore[arg-type]

    def test_is_empty_is_false_when_populated(self) -> None:
        assert self._suggestion_set().is_empty is False

    def test_is_empty_is_true_when_no_medications(self) -> None:
        assert self._suggestion_set(medications=()).is_empty is True


class TestPrescriptionTemplateSet:
    def test_constructs_with_all_fields(self) -> None:
        template_set = PrescriptionTemplateSet(
            system_template_name="prescription_suggestion.outpatient.system",
            developer_template_name="prescription_suggestion.outpatient.developer",
            user_template_name="prescription_suggestion.outpatient.user",
            version=1,
        )
        assert template_set.version == 1
        assert template_set.system_template_name == "prescription_suggestion.outpatient.system"


class TestGenerationSession:
    def _session(self, **overrides: object) -> GenerationSession:
        defaults: dict[str, object] = {
            "generation_id": uuid4(),
            "provider": "mock",
            "model": "mock-model",
            "prescribing_setting": "outpatient",
            "language": "en",
            "status": GenerationStatus.COMPLETED,
        }
        defaults.update(overrides)
        return GenerationSession(**defaults)  # type: ignore[arg-type]

    def test_constructs_with_defaults_for_metrics(self) -> None:
        session = self._session()
        assert session.latency_ms == 0.0
        assert session.prompt_tokens == 0
        assert session.estimated_cost_usd == 0.0
        assert session.created_at is not None

    def test_accepts_full_metrics(self) -> None:
        session = self._session(
            latency_ms=42.5,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            estimated_cost_usd=0.0021,
        )
        assert session.latency_ms == 42.5
        assert session.total_tokens == 150

    def test_different_generation_ids_are_never_equal(self) -> None:
        a = self._session(generation_id=uuid4())
        b = self._session(generation_id=uuid4())
        assert a != b


class TestPrescriptionStreamChunk:
    def test_defaults_is_final_to_false(self) -> None:
        chunk = PrescriptionStreamChunk(delta="hello")
        assert chunk.is_final is False

    def test_accepts_is_final_true(self) -> None:
        chunk = PrescriptionStreamChunk(delta="", is_final=True)
        assert chunk.is_final is True

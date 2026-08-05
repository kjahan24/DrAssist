"""Tests for `DischargeInstructionService`."""

from app.modules.patient_education_ai.application.services.discharge_instruction_service import (
    DischargeInstructionService,
)
from tests.unit.modules.patient_education_ai.application.fakes import (
    FakeDischargeInstructionPort,
)


class TestCollectMedicationInstructions:
    def test_returns_empty_tuple_when_none_recognized(self) -> None:
        service = DischargeInstructionService(
            discharge_instruction_port=FakeDischargeInstructionPort()
        )
        assert service.collect_medication_instructions(("Unknown Drug",)) == ()

    def test_returns_curated_instruction_for_a_single_medication(self) -> None:
        port = FakeDischargeInstructionPort(medication_instruction="Take with food.")
        service = DischargeInstructionService(discharge_instruction_port=port)

        result = service.collect_medication_instructions(("Metformin",))

        assert result == ("Take with food.",)

    def test_queries_port_once_per_medication(self) -> None:
        port = FakeDischargeInstructionPort(medication_instruction="Take with food.")
        service = DischargeInstructionService(discharge_instruction_port=port)

        service.collect_medication_instructions(("Metformin", "Lisinopril"))

        assert port.instruct_medication_calls == ["Metformin", "Lisinopril"]

    def test_deduplicates_identical_instructions(self) -> None:
        port = FakeDischargeInstructionPort(medication_instruction="Take with food.")
        service = DischargeInstructionService(discharge_instruction_port=port)

        result = service.collect_medication_instructions(("Metformin", "Insulin"))

        assert result == ("Take with food.",)


class TestCollectHomeCarePlan:
    def test_delegates_to_port(self) -> None:
        port = FakeDischargeInstructionPort(home_care_instructions=("Rest and hydrate.",))
        service = DischargeInstructionService(discharge_instruction_port=port)

        assert service.collect_home_care_plan(("Pneumonia",)) == ("Rest and hydrate.",)

    def test_empty_when_port_returns_nothing(self) -> None:
        service = DischargeInstructionService(
            discharge_instruction_port=FakeDischargeInstructionPort()
        )
        assert service.collect_home_care_plan(("Unknown",)) == ()


class TestCollectPatientChecklist:
    def test_delegates_to_port(self) -> None:
        port = FakeDischargeInstructionPort(discharge_checklist=("Fill your prescriptions.",))
        service = DischargeInstructionService(discharge_instruction_port=port)

        assert service.collect_patient_checklist(("Diabetes",)) == ("Fill your prescriptions.",)

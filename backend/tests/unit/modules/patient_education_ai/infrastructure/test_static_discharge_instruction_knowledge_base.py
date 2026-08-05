"""Unit tests for `StaticDischargeInstructionKnowledgeBase`."""

import pytest

from app.modules.patient_education_ai.infrastructure.discharge_instruction.static_discharge_instruction_knowledge_base import (  # noqa: E501
    StaticDischargeInstructionKnowledgeBase,
)

_KB = StaticDischargeInstructionKnowledgeBase()

_RECOGNIZED_MEDICATIONS = (
    "metformin",
    "lisinopril",
    "atorvastatin",
    "aspirin",
    "warfarin",
    "insulin",
    "albuterol",
    "amoxicillin",
    "ibuprofen",
    "omeprazole",
)


class TestInstructMedication:
    @pytest.mark.parametrize("medication", _RECOGNIZED_MEDICATIONS)
    def test_returns_an_instruction_for_every_recognized_medication(self, medication: str) -> None:
        instruction = _KB.instruct_medication(medication)
        assert instruction is not None
        assert instruction.strip()

    def test_returns_none_for_an_unrecognized_medication(self) -> None:
        assert _KB.instruct_medication("Some Unrecognized Drug") is None

    def test_matches_case_insensitively(self) -> None:
        assert _KB.instruct_medication("METFORMIN") is not None

    def test_matches_by_substring_to_tolerate_dose_suffixes(self) -> None:
        assert _KB.instruct_medication("Metformin 500mg") is not None


class TestGenerateHomeCareInstructions:
    def test_returns_instructions_for_a_recognized_diagnosis(self) -> None:
        assert len(_KB.generate_home_care_instructions(("Heart Failure",))) > 0

    def test_returns_empty_tuple_for_an_unrecognized_diagnosis(self) -> None:
        assert _KB.generate_home_care_instructions(("Some Unrecognized Condition",)) == ()

    def test_returns_wound_care_instructions_for_surgery(self) -> None:
        result = _KB.generate_home_care_instructions(("Post-surgery recovery",))
        assert any("incision" in item.lower() for item in result)

    def test_deduplicates_across_diagnoses(self) -> None:
        result = _KB.generate_home_care_instructions(("Surgery", "Wound infection"))
        assert len(result) == len(set(result))


class TestGenerateDischargeChecklist:
    def test_always_includes_the_base_checklist(self) -> None:
        result = _KB.generate_discharge_checklist(("Some Unrecognized Condition",))
        assert len(result) == 3

    def test_adds_diagnosis_specific_items(self) -> None:
        result = _KB.generate_discharge_checklist(("Diabetes",))
        assert len(result) > 3
        assert any("blood sugar monitor" in item.lower() for item in result)

    def test_deduplicates_across_diagnoses(self) -> None:
        result = _KB.generate_discharge_checklist(("Surgery", "Wound"))
        assert len(result) == len(set(result))

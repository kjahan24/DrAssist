"""`DischargeInstructionService` — this task's own explicitly-named
APPLICATION service, the thin orchestration layer over
`DischargeInstructionPort`:

- `collect_medication_instructions` — this task's own "Medication
  Instructions" OUTPUT field (covering both "Medication instructions"
  and "Medication adherence guidance" GENERATE items, per that port's
  own docstring): one curated instruction per recognized current
  medication, skipping any medication the port has no reference data
  for.
- `collect_home_care_plan` — this task's own "Home Care Plan" OUTPUT
  field (covering both "Home care instructions" and "Wound care
  instructions" GENERATE items — this task's own OUTPUT section names
  only one field for both, so both fold into this one collection, the
  same "several consecutively-listed GENERATE items collapse onto one
  OUTPUT field" reading every prior AI module's own OUTPUT-mapping
  design documents for itself).
- `collect_patient_checklist` — this task's own "Patient Checklist"
  OUTPUT field (covering "Discharge checklist").
"""

from app.modules.patient_education_ai.application.ports import DischargeInstructionPort
from app.modules.patient_education_ai.application.services._dedupe import (
    dedupe_preserving_order,
)


class DischargeInstructionService:
    def __init__(self, *, discharge_instruction_port: DischargeInstructionPort) -> None:
        self._discharge_instruction_port = discharge_instruction_port

    def collect_medication_instructions(self, medications: tuple[str, ...]) -> tuple[str, ...]:
        instructions = [
            instruction
            for medication in medications
            if (instruction := self._discharge_instruction_port.instruct_medication(medication))
            is not None
        ]
        return dedupe_preserving_order(tuple(instructions))

    def collect_home_care_plan(self, diagnoses: tuple[str, ...]) -> tuple[str, ...]:
        return self._discharge_instruction_port.generate_home_care_instructions(diagnoses)

    def collect_patient_checklist(self, diagnoses: tuple[str, ...]) -> tuple[str, ...]:
        return self._discharge_instruction_port.generate_discharge_checklist(diagnoses)

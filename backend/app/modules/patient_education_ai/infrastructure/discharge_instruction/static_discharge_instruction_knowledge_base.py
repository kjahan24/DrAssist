"""`StaticDischargeInstructionKnowledgeBase` — the one concrete
`DischargeInstructionPort` implementation this task ships: a curated,
necessarily-incomplete reference table of medication-taking/adherence
instructions (keyed by medication name) and home-care/discharge-
checklist content (keyed by diagnosis keyword), the same "each module
defines its own local, necessarily-incomplete copy" precedent every
prior AI module's own knowledge-base adapter establishes for itself.

`generate_discharge_checklist` always includes a small, diagnosis-
independent base checklist (filling prescriptions, scheduling
follow-up, knowing warning signs) in addition to whatever
diagnosis-specific items match — a discharge checklist has a generic
core regardless of diagnosis, unlike `explain_diagnosis`/
`instruct_medication`, which have nothing sensible to say about an
unrecognized diagnosis/medication.
"""

from app.modules.patient_education_ai.application.ports import DischargeInstructionPort

_MEDICATION_INSTRUCTIONS: dict[str, str] = {
    "metformin": (
        "Take metformin with food to reduce stomach upset, and do not stop taking it "
        "without talking to your doctor."
    ),
    "lisinopril": (
        "Take lisinopril at the same time each day, and call your doctor if you notice "
        "swelling of your face or throat."
    ),
    "atorvastatin": (
        "Take atorvastatin as directed, usually in the evening, and report any unexplained "
        "muscle pain to your doctor."
    ),
    "aspirin": (
        "Take aspirin exactly as prescribed and tell your doctor about any unusual bruising "
        "or bleeding."
    ),
    "warfarin": (
        "Take warfarin at the same time every day, keep your follow-up blood test "
        "appointments, and watch for unusual bruising or bleeding."
    ),
    "insulin": (
        "Take insulin exactly as prescribed, check your blood sugar as instructed, and "
        "carry a fast-acting sugar source with you."
    ),
    "albuterol": (
        "Use your albuterol inhaler as directed for symptoms, and contact your doctor if "
        "you are using it more often than prescribed."
    ),
    "amoxicillin": (
        "Finish the entire course of amoxicillin even if you start feeling better, unless "
        "your doctor tells you otherwise."
    ),
    "ibuprofen": (
        "Take ibuprofen with food, and do not exceed the dose printed on the label or "
        "prescribed by your doctor."
    ),
    "omeprazole": (
        "Take omeprazole before a meal, usually in the morning, as directed by your doctor."
    ),
}

_HOME_CARE_BY_DIAGNOSIS: dict[str, tuple[str, ...]] = {
    "hypertension": ("Check and record your blood pressure at home as instructed.",),
    "diabetes": ("Check your blood sugar as instructed and keep a log of your readings.",),
    "asthma": ("Keep your rescue inhaler with you at all times.",),
    "copd": ("Use your prescribed inhalers on schedule, not just when you feel short of breath.",),
    "heart failure": (
        "Weigh yourself daily and call your doctor if you gain 2-3 pounds in a day.",
    ),
    "pneumonia": ("Rest and stay well hydrated while you recover.",),
    "urinary tract infection": ("Drink plenty of water to help flush your urinary system.",),
    "coronary artery disease": ("Keep nitroglycerin with you if it was prescribed.",),
    "chronic kidney disease": ("Follow any fluid or salt restrictions your doctor gave you.",),
    "stroke": ("Follow your prescribed rehabilitation exercises at home.",),
    "surgery": ("Keep your incision clean and dry, and watch for signs of infection.",),
    "wound": ("Change your wound dressing as instructed and watch for signs of infection.",),
}

_BASE_DISCHARGE_CHECKLIST: tuple[str, ...] = (
    "Fill all new prescriptions before you need your next dose.",
    "Schedule your follow-up appointment as instructed.",
    "Know your warning signs and when to seek help.",
)

_CHECKLIST_BY_DIAGNOSIS: dict[str, tuple[str, ...]] = {
    "diabetes": ("Arrange a blood sugar monitor and testing supplies.",),
    "heart failure": ("Arrange a daily weight scale at home.",),
    "surgery": ("Arrange help at home for the first few days after surgery.",),
    "wound": ("Arrange wound care supplies for dressing changes.",),
}


class StaticDischargeInstructionKnowledgeBase(DischargeInstructionPort):
    def instruct_medication(self, medication: str) -> str | None:
        normalized = medication.strip().lower()
        for keyword, instruction in _MEDICATION_INSTRUCTIONS.items():
            if keyword in normalized:
                return instruction
        return None

    def generate_home_care_instructions(self, diagnoses: tuple[str, ...]) -> tuple[str, ...]:
        instructions: list[str] = []
        for diagnosis in diagnoses:
            normalized = diagnosis.strip().lower()
            for keyword, items in _HOME_CARE_BY_DIAGNOSIS.items():
                if keyword in normalized:
                    instructions.extend(items)
        return tuple(dict.fromkeys(instructions))

    def generate_discharge_checklist(self, diagnoses: tuple[str, ...]) -> tuple[str, ...]:
        checklist: list[str] = list(_BASE_DISCHARGE_CHECKLIST)
        for diagnosis in diagnoses:
            normalized = diagnosis.strip().lower()
            for keyword, items in _CHECKLIST_BY_DIAGNOSIS.items():
                if keyword in normalized:
                    checklist.extend(items)
        return tuple(dict.fromkeys(checklist))

"""`StaticMedicationKnowledgeBase` — the one concrete
`MedicationKnowledgePort` implementation this task ships. See that
port's own docstring (`application/ports.py`) for why neither of its
methods is a hard validation gate.

`_THERAPEUTIC_CLASSES` is a small curated reference table mapping common
generic medication names to their therapeutic class — used by
`application/services/medication_safety_analysis_service.py`'s duplicate-
therapy check. A real production system would call a licensed,
regularly-updated drug formulary/knowledge-base API here instead; this
module's own small, self-contained implementation is the pragmatic
in-repo substitute, the same "each module defines its own local,
necessarily-incomplete copy" precedent
`app.modules.icd10_ai.infrastructure.knowledge.icd10_knowledge_base
.StaticICD10KnowledgeBase` already establishes for its own module.
"""

from app.modules.prescription_ai.application.ports import MedicationKnowledgePort

_THERAPEUTIC_CLASSES: dict[str, str] = {
    "ibuprofen": "NSAID",
    "naproxen": "NSAID",
    "aspirin": "NSAID",
    "diclofenac": "NSAID",
    "acetaminophen": "Analgesic (non-opioid)",
    "amoxicillin": "Penicillin antibiotic",
    "amoxicillin-clavulanate": "Penicillin antibiotic",
    "penicillin": "Penicillin antibiotic",
    "ampicillin": "Penicillin antibiotic",
    "azithromycin": "Macrolide antibiotic",
    "clarithromycin": "Macrolide antibiotic",
    "erythromycin": "Macrolide antibiotic",
    "ciprofloxacin": "Fluoroquinolone antibiotic",
    "levofloxacin": "Fluoroquinolone antibiotic",
    "lisinopril": "ACE inhibitor",
    "enalapril": "ACE inhibitor",
    "ramipril": "ACE inhibitor",
    "losartan": "ARB",
    "valsartan": "ARB",
    "metoprolol": "Beta blocker",
    "atenolol": "Beta blocker",
    "propranolol": "Beta blocker",
    "amlodipine": "Calcium channel blocker",
    "diltiazem": "Calcium channel blocker",
    "metformin": "Biguanide antidiabetic",
    "glipizide": "Sulfonylurea antidiabetic",
    "glyburide": "Sulfonylurea antidiabetic",
    "atorvastatin": "Statin",
    "simvastatin": "Statin",
    "rosuvastatin": "Statin",
    "omeprazole": "Proton pump inhibitor",
    "pantoprazole": "Proton pump inhibitor",
    "esomeprazole": "Proton pump inhibitor",
    "sertraline": "SSRI",
    "fluoxetine": "SSRI",
    "escitalopram": "SSRI",
    "paroxetine": "SSRI",
    "warfarin": "Anticoagulant",
    "apixaban": "Anticoagulant",
    "rivaroxaban": "Anticoagulant",
    "prednisone": "Corticosteroid",
    "prednisolone": "Corticosteroid",
    "albuterol": "Short-acting beta agonist bronchodilator",
    "montelukast": "Leukotriene receptor antagonist",
    "hydrochlorothiazide": "Thiazide diuretic",
    "furosemide": "Loop diuretic",
    "spironolactone": "Potassium-sparing diuretic",
    "tramadol": "Opioid analgesic",
    "oxycodone": "Opioid analgesic",
    "hydrocodone": "Opioid analgesic",
    "morphine": "Opioid analgesic",
    "gabapentin": "Anticonvulsant/neuropathic pain agent",
    "cetirizine": "Second-generation antihistamine",
    "loratadine": "Second-generation antihistamine",
    "diphenhydramine": "First-generation antihistamine",
}


class StaticMedicationKnowledgeBase(MedicationKnowledgePort):
    def is_known_medication(self, generic_name: str) -> bool:
        return generic_name.strip().lower() in _THERAPEUTIC_CLASSES

    def lookup_therapeutic_class(self, generic_name: str) -> str | None:
        return _THERAPEUTIC_CLASSES.get(generic_name.strip().lower())

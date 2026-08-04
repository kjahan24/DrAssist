"""`StaticICD10KnowledgeBase` — the one concrete `ICD10KnowledgePort`
implementation this task ships. See that port's own docstring
(`application/ports.py`) for the full split between its two methods.

`_FORMAT_PATTERN` encodes the general ICD-10-CM code shape: a category
of one letter (`A`-`T` or `V`-`Z` — `U` is reserved by the WHO and never
assigned) followed by two alphanumeric characters, optionally followed by
a decimal point and up to four further alphanumeric characters (e.g.
`"J06.9"`, `"I10"`, `"S72.001A"`). This is a *structural* check, not a
lookup against the full ~70,000-code catalog — a real production system
would call a licensed, regularly-updated ICD-10-CM database/API here
instead; this module's own small, self-contained implementation is the
pragmatic in-repo substitute, the same "each module defines its own
local, necessarily-incomplete copy" precedent
`app.modules.soap_note_ai.infrastructure.cost.cost_estimator.CostEstimator`
already establishes for its own pricing table.

`_COMMON_CODES` is a small curated reference set of frequently-seen
ICD-10-CM codes with their canonical descriptions, used only as a *soft*
"is this a recognized common code" signal by
`application/services/icd10_ranking_service.py` — never as a hard
validation gate (see `is_valid_format` vs. `lookup_canonical_name` in the
port's own docstring for why).
"""

import re

from app.modules.icd10_ai.application.ports import ICD10KnowledgePort

_FORMAT_PATTERN = re.compile(r"^[A-TV-Z][0-9][0-9A-Z](\.[0-9A-Z]{1,4})?$")

_COMMON_CODES: dict[str, str] = {
    "J06.9": "Acute upper respiratory infection, unspecified",
    "J45.909": "Unspecified asthma, uncomplicated",
    "J45.20": "Mild intermittent asthma, uncomplicated",
    "I10": "Essential (primary) hypertension",
    "E11.9": "Type 2 diabetes mellitus without complications",
    "E78.5": "Hyperlipidemia, unspecified",
    "R51": "Headache",
    "R51.9": "Headache, unspecified",
    "M54.5": "Low back pain",
    "M54.50": "Low back pain, unspecified",
    "N39.0": "Urinary tract infection, site not specified",
    "K21.9": "Gastro-esophageal reflux disease without esophagitis",
    "F41.9": "Anxiety disorder, unspecified",
    "F32.9": "Major depressive disorder, single episode, unspecified",
    "R05": "Cough",
    "R05.9": "Cough, unspecified",
    "R10.9": "Unspecified abdominal pain",
    "J02.9": "Acute pharyngitis, unspecified",
    "J20.9": "Acute bronchitis, unspecified",
    "R50.9": "Fever, unspecified",
    "H66.90": "Otitis media, unspecified, unspecified ear",
    "L30.9": "Dermatitis, unspecified",
    "M25.50": "Pain in unspecified joint",
    "R11.0": "Nausea",
    "R11.2": "Nausea with vomiting, unspecified",
    "I63.9": "Cerebral infarction, unspecified",
    "O80": "Encounter for full-term uncomplicated delivery",
    "Z00.00": "Encounter for general adult medical examination without abnormal findings",
}


class StaticICD10KnowledgeBase(ICD10KnowledgePort):
    def is_valid_format(self, icd10_code: str) -> bool:
        return bool(_FORMAT_PATTERN.match(icd10_code.strip().upper()))

    def lookup_canonical_name(self, icd10_code: str) -> str | None:
        return _COMMON_CODES.get(icd10_code.strip().upper())

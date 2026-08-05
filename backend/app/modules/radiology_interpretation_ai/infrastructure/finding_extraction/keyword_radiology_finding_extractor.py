"""`KeywordRadiologyFindingExtractor` — the one concrete
`FindingExtractionPort` implementation this task ships: a small, curated
keyword table scanned against report text. A real production system
might instead consult a structured clinical-terminology/NLP model here;
this module's own small, rule-based implementation is the pragmatic
in-repo substitute, the same "each module defines its own local,
necessarily-incomplete copy" precedent
`app.modules.lab_interpretation_ai.infrastructure.critical_values
.static_critical_value_analyzer.StaticCriticalValueAnalyzer` establishes
for numeric lab values, applied here to free text instead.

`_CRITICAL_KEYWORDS`/`_NORMAL_KEYWORDS` are deliberately chosen so no
entry is a substring of another entry in the same table — this keeps
`extract_candidate_findings` from reporting the same underlying mention
twice (once for a specific phrase, once for a more general one nested
inside it) without needing extra deduplication logic.
"""

from app.modules.radiology_interpretation_ai.application.ports import FindingExtractionPort
from app.modules.radiology_interpretation_ai.domain.enums import RadiologyFindingCategory
from app.modules.radiology_interpretation_ai.domain.value_objects import RadiologyFinding

_CRITICAL_KEYWORDS = (
    "pneumothorax",
    "hemorrhage",
    "rupture",
    "perforation",
    "obstruction",
    "mass effect",
    "midline shift",
    "herniation",
    "embolism",
    "dissection",
    "free air",
    "tamponade",
)

_NORMAL_KEYWORDS = (
    "no acute findings",
    "unremarkable",
    "within normal limits",
    "no significant abnormality",
    "no acute abnormality",
    "normal study",
)


class KeywordRadiologyFindingExtractor(FindingExtractionPort):
    def __init__(
        self,
        *,
        critical_keywords: tuple[str, ...] | None = None,
        normal_keywords: tuple[str, ...] | None = None,
    ) -> None:
        self._critical_keywords = critical_keywords or _CRITICAL_KEYWORDS
        self._normal_keywords = normal_keywords or _NORMAL_KEYWORDS

    def extract_candidate_findings(self, report_text: str) -> tuple[RadiologyFinding, ...]:
        text_lower = report_text.lower()
        candidates: list[RadiologyFinding] = []
        for keyword in self._critical_keywords:
            if keyword in text_lower:
                candidates.append(
                    RadiologyFinding(
                        description=keyword.capitalize(), category=RadiologyFindingCategory.CRITICAL
                    )
                )
        for keyword in self._normal_keywords:
            if keyword in text_lower:
                candidates.append(
                    RadiologyFinding(
                        description=keyword.capitalize(), category=RadiologyFindingCategory.NORMAL
                    )
                )
        return tuple(candidates)

    def classify_description(self, description: str) -> RadiologyFindingCategory | None:
        text_lower = description.lower()
        for keyword in self._critical_keywords:
            if keyword in text_lower:
                return RadiologyFindingCategory.CRITICAL
        for keyword in self._normal_keywords:
            if keyword in text_lower:
                return RadiologyFindingCategory.NORMAL
        return None

"""`KeywordClinicalCorrelator` — the one concrete `ClinicalCorrelationPort`
implementation this task ships: a small, curated keyword table scanned
against report text. A real production system might instead consult a
structured clinical-terminology/NLP model here (ideally with negation
detection — this simple substring scanner has no such handling, so a
report phrase like "no evidence of malignancy" would still trigger the
"malignancy" keyword; a genuine limitation this module's own docstrings
document rather than silently paper over); this module's own small,
rule-based implementation is the pragmatic in-repo substitute, the same
"each module defines its own local, necessarily-incomplete copy"
precedent `app.modules.radiology_interpretation_ai.infrastructure
.finding_extraction.keyword_radiology_finding_extractor
.KeywordRadiologyFindingExtractor` establishes for itself, applied here
to pathology-specific vocabulary.

`_MALIGNANT_KEYWORDS`/`_BENIGN_KEYWORDS` are deliberately chosen so no
entry is a substring of another entry in the same table — this keeps
`extract_candidate_findings` from reporting the same underlying mention
twice (once for a specific phrase, once for a more general one nested
inside it) without needing extra deduplication logic.
"""

from app.modules.pathology_interpretation_ai.application.ports import ClinicalCorrelationPort
from app.modules.pathology_interpretation_ai.domain.enums import PathologyFindingCategory
from app.modules.pathology_interpretation_ai.domain.value_objects import PathologyFinding

_MALIGNANT_KEYWORDS = (
    "malignant",
    "carcinoma",
    "sarcoma",
    "lymphoma",
    "melanoma",
    "metastatic",
    "metastasis",
    "invasive",
    "malignancy",
)

_BENIGN_KEYWORDS = (
    "benign",
    "unremarkable",
    "reactive changes",
    "within normal limits",
    "no significant abnormality",
    "normal histology",
)


class KeywordClinicalCorrelator(ClinicalCorrelationPort):
    def __init__(
        self,
        *,
        malignant_keywords: tuple[str, ...] | None = None,
        benign_keywords: tuple[str, ...] | None = None,
    ) -> None:
        self._malignant_keywords = malignant_keywords or _MALIGNANT_KEYWORDS
        self._benign_keywords = benign_keywords or _BENIGN_KEYWORDS

    def extract_candidate_findings(self, report_text: str) -> tuple[PathologyFinding, ...]:
        text_lower = report_text.lower()
        candidates: list[PathologyFinding] = []
        for keyword in self._malignant_keywords:
            if keyword in text_lower:
                candidates.append(
                    PathologyFinding(
                        description=keyword.capitalize(),
                        category=PathologyFindingCategory.MALIGNANT,
                    )
                )
        for keyword in self._benign_keywords:
            if keyword in text_lower:
                candidates.append(
                    PathologyFinding(
                        description=keyword.capitalize(), category=PathologyFindingCategory.BENIGN
                    )
                )
        return tuple(candidates)

    def classify_description(self, description: str) -> PathologyFindingCategory | None:
        text_lower = description.lower()
        for keyword in self._malignant_keywords:
            if keyword in text_lower:
                return PathologyFindingCategory.MALIGNANT
        for keyword in self._benign_keywords:
            if keyword in text_lower:
                return PathologyFindingCategory.BENIGN
        return None

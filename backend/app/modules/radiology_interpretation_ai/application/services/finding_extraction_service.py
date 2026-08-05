"""`FindingExtractionService` — this task's own explicitly-named
APPLICATION service, a thin wrapper over `FindingExtractionPort` (see
that port's own docstring in `application/ports.py` for the full
reasoning). "Finding extraction" is fundamentally the AI's own semantic
reading of the report — this service's own contribution is the
deterministic, keyword-driven second read used as a safety net elsewhere
(`CriticalFindingDetectionService`), not a replacement for the AI's own
extraction.
"""

from app.modules.radiology_interpretation_ai.application.ports import FindingExtractionPort
from app.modules.radiology_interpretation_ai.domain.value_objects import RadiologyFinding


class FindingExtractionService:
    def __init__(self, *, extractor: FindingExtractionPort) -> None:
        self._extractor = extractor

    def extract(self, report_text: str) -> tuple[RadiologyFinding, ...]:
        return self._extractor.extract_candidate_findings(report_text)

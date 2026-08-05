"""`FindingExtractionService` — this task's own explicitly-named
APPLICATION service, a thin wrapper over `ClinicalCorrelationPort` (see
that port's own docstring in `application/ports.py` for the full
reasoning). "Finding extraction" is fundamentally the AI's own semantic
reading of the report — this service's own contribution is the
deterministic, keyword-driven second read used as a safety net elsewhere
(`MalignancyAssessmentService`), not a replacement for the AI's own
extraction.
"""

from app.modules.pathology_interpretation_ai.application.ports import ClinicalCorrelationPort
from app.modules.pathology_interpretation_ai.domain.value_objects import PathologyFinding


class FindingExtractionService:
    def __init__(self, *, correlator: ClinicalCorrelationPort) -> None:
        self._correlator = correlator

    def extract(self, report_text: str) -> tuple[PathologyFinding, ...]:
        return self._correlator.extract_candidate_findings(report_text)

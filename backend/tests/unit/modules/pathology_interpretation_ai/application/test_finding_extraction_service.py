"""Unit tests for `FindingExtractionService`."""

from app.modules.pathology_interpretation_ai.application.services.finding_extraction_service import (  # noqa: E501
    FindingExtractionService,
)
from tests.unit.modules.pathology_interpretation_ai.application.fakes import (
    FakeClinicalCorrelationPort,
    make_finding,
)


class TestExtract:
    def test_delegates_to_the_correlator_port(self) -> None:
        candidates = (make_finding(description="Invasive carcinoma"),)
        correlator = FakeClinicalCorrelationPort(candidates=candidates)
        service = FindingExtractionService(correlator=correlator)

        result = service.extract("some report text")

        assert result == candidates
        assert correlator.extract_calls == ["some report text"]

    def test_returns_empty_tuple_when_nothing_is_extracted(self) -> None:
        service = FindingExtractionService(correlator=FakeClinicalCorrelationPort())
        assert service.extract("unremarkable specimen") == ()

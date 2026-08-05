"""Unit tests for `FindingExtractionService`."""

from app.modules.radiology_interpretation_ai.application.services.finding_extraction_service import (  # noqa: E501
    FindingExtractionService,
)
from tests.unit.modules.radiology_interpretation_ai.application.fakes import (
    FakeFindingExtractionPort,
    make_finding,
)


class TestExtract:
    def test_delegates_to_the_extractor_port(self) -> None:
        candidates = (make_finding(description="Pneumothorax"),)
        extractor = FakeFindingExtractionPort(candidates=candidates)
        service = FindingExtractionService(extractor=extractor)

        result = service.extract("some report text")

        assert result == candidates
        assert extractor.extract_calls == ["some report text"]

    def test_returns_empty_tuple_when_nothing_is_extracted(self) -> None:
        service = FindingExtractionService(extractor=FakeFindingExtractionPort())
        assert service.extract("unremarkable study") == ()

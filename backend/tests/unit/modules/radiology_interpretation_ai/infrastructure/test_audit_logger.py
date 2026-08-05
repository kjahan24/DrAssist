"""Unit tests for `StructlogRadiologyInterpretationAuditLogger` —
verifies it logs without raising for both the success and failure
paths."""

from uuid import uuid4

from app.modules.radiology_interpretation_ai.infrastructure.audit.audit_logger import (
    StructlogRadiologyInterpretationAuditLogger,
)
from tests.unit.modules.radiology_interpretation_ai.application.fakes import (
    make_generation_session,
)


class TestStructlogRadiologyInterpretationAuditLogger:
    async def test_log_generation_does_not_raise(self) -> None:
        logger = StructlogRadiologyInterpretationAuditLogger()
        await logger.log_generation(
            make_generation_session(), organization_id=uuid4(), patient_id=uuid4()
        )

    async def test_log_failure_does_not_raise(self) -> None:
        logger = StructlogRadiologyInterpretationAuditLogger()
        await logger.log_failure(
            generation_id=uuid4(),
            organization_id=uuid4(),
            patient_id=uuid4(),
            stage="parse_or_validate",
            error_code="InvalidRadiologyInterpretationResponseFormatError",
            message="malformed JSON",
        )

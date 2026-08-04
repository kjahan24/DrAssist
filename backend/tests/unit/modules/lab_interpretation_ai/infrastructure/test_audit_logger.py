"""Unit tests for `StructlogLabInterpretationAuditLogger` — verifies it
logs without raising for both the success and failure paths."""

from uuid import uuid4

from app.modules.lab_interpretation_ai.infrastructure.audit.audit_logger import (
    StructlogLabInterpretationAuditLogger,
)
from tests.unit.modules.lab_interpretation_ai.application.fakes import make_generation_session


class TestStructlogLabInterpretationAuditLogger:
    async def test_log_generation_does_not_raise(self) -> None:
        logger = StructlogLabInterpretationAuditLogger()
        await logger.log_generation(
            make_generation_session(), organization_id=uuid4(), patient_id=uuid4()
        )

    async def test_log_failure_does_not_raise(self) -> None:
        logger = StructlogLabInterpretationAuditLogger()
        await logger.log_failure(
            generation_id=uuid4(),
            organization_id=uuid4(),
            patient_id=uuid4(),
            stage="parse_or_validate",
            error_code="InvalidLabInterpretationResponseFormatError",
            message="malformed JSON",
        )

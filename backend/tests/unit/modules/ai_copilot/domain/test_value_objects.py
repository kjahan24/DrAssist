"""Unit tests for the AI Clinical Copilot module's domain value objects."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.modules.ai_copilot.domain.enums import CopilotOutputFormat
from app.modules.ai_copilot.domain.exceptions import InvalidAIRequestError
from app.modules.ai_copilot.domain.value_objects import AIRequest, AISession


class TestAIRequest:
    def test_constructs_with_required_fields(self) -> None:
        patient_id = uuid4()
        request = AIRequest(request_type="generic", patient_id=patient_id, prompt_version=1)
        assert request.request_type == "generic"
        assert request.patient_id == patient_id
        assert request.prompt_version == 1
        assert request.output_format is CopilotOutputFormat.JSON
        assert request.visit_id is None
        assert request.model_override is None
        assert dict(request.variables) == {}

    def test_accepts_optional_fields(self) -> None:
        visit_id = uuid4()
        request = AIRequest(
            request_type="generic",
            patient_id=uuid4(),
            prompt_version=2,
            output_format=CopilotOutputFormat.MARKDOWN,
            visit_id=visit_id,
            model_override="gpt-4o",
            variables={"tone": "concise"},
        )
        assert request.output_format is CopilotOutputFormat.MARKDOWN
        assert request.visit_id == visit_id
        assert request.model_override == "gpt-4o"
        assert request.variables == {"tone": "concise"}

    @pytest.mark.parametrize("request_type", ["", "   "])
    def test_rejects_blank_request_type(self, request_type: str) -> None:
        with pytest.raises(InvalidAIRequestError):
            AIRequest(request_type=request_type, patient_id=uuid4(), prompt_version=1)

    @pytest.mark.parametrize("prompt_version", [0, -1])
    def test_rejects_prompt_version_below_one(self, prompt_version: int) -> None:
        with pytest.raises(InvalidAIRequestError):
            AIRequest(request_type="generic", patient_id=uuid4(), prompt_version=prompt_version)

    def test_equality_is_by_value(self) -> None:
        patient_id = uuid4()
        a = AIRequest(request_type="generic", patient_id=patient_id, prompt_version=1)
        b = AIRequest(request_type="generic", patient_id=patient_id, prompt_version=1)
        assert a == b

    def test_default_variables_are_not_shared_across_instances(self) -> None:
        """Guards against a `mutable default` bug: `field(default_factory=dict)`
        must build a fresh dict per instance, not one shared empty dict."""
        a = AIRequest(request_type="generic", patient_id=uuid4(), prompt_version=1)
        b = AIRequest(request_type="generic", patient_id=uuid4(), prompt_version=1)
        assert a.variables is not b.variables

    def test_accepts_a_prompt_version_of_exactly_one(self) -> None:
        request = AIRequest(request_type="generic", patient_id=uuid4(), prompt_version=1)
        assert request.prompt_version == 1


class TestAISession:
    def test_constructs_with_all_tracked_fields(self) -> None:
        request_id = uuid4()
        session = AISession(
            request_id=request_id,
            provider="mock",
            model="mock-model",
            prompt_name="generic",
            prompt_version=1,
            latency_ms=12.5,
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            estimated_cost_usd=0.001,
        )
        assert session.request_id == request_id
        assert session.provider == "mock"
        assert session.model == "mock-model"
        assert session.prompt_name == "generic"
        assert session.prompt_version == 1
        assert session.latency_ms == 12.5
        assert session.prompt_tokens == 10
        assert session.completion_tokens == 5
        assert session.total_tokens == 15
        assert session.estimated_cost_usd == 0.001
        assert session.created_at is not None

    def test_equality_is_by_value(self) -> None:
        request_id = uuid4()
        kwargs = {
            "request_id": request_id,
            "provider": "mock",
            "model": "mock-model",
            "prompt_name": "generic",
            "prompt_version": 1,
            "latency_ms": 1.0,
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "total_tokens": 2,
            "estimated_cost_usd": 0.0,
        }
        created_at = datetime.now(UTC)
        a = AISession(**kwargs, created_at=created_at)  # type: ignore[arg-type]
        b = AISession(**kwargs, created_at=created_at)  # type: ignore[arg-type]
        assert a == b

    def test_different_request_ids_are_never_equal(self) -> None:
        kwargs = {
            "provider": "mock",
            "model": "mock-model",
            "prompt_name": "generic",
            "prompt_version": 1,
            "latency_ms": 1.0,
            "prompt_tokens": 1,
            "completion_tokens": 1,
            "total_tokens": 2,
            "estimated_cost_usd": 0.0,
        }
        a = AISession(request_id=uuid4(), **kwargs)  # type: ignore[arg-type]
        b = AISession(request_id=uuid4(), **kwargs)  # type: ignore[arg-type]
        assert a != b

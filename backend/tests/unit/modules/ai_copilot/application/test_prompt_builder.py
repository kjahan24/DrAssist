"""Unit tests for `PromptBuilder`."""

from uuid import uuid4

import pytest

from app.modules.ai.public.dto import AIMessageRole
from app.modules.ai_copilot.application.dto import ClinicalContext
from app.modules.ai_copilot.application.services.prompt_builder import PromptBuilder
from tests.unit.modules.ai_copilot.application.fakes import (
    FakeAIGateway,
    make_allergy_summary,
    make_clinical_note_summary,
    make_condition_summary,
    make_lab_result_summary,
    make_patient_summary,
    make_prescription_summary,
    make_soap_note_summary,
    make_timeline_event,
    make_visit_summary,
)


def _empty_context() -> ClinicalContext:
    patient = make_patient_summary()
    return ClinicalContext(
        patient=patient,
        allergies=(),
        medications=(),
        conditions=(),
        visits=(),
        clinical_notes=(),
        soap_notes=(),
        lab_results=(),
        timeline_events=(),
    )


def _full_context() -> ClinicalContext:
    patient_id = uuid4()
    patient = make_patient_summary(patient_id=patient_id)
    note = make_clinical_note_summary(patient_id=patient_id)
    return ClinicalContext(
        patient=patient,
        allergies=(make_allergy_summary(patient_id=patient_id),),
        medications=(make_prescription_summary(patient_id=patient_id),),
        conditions=(make_condition_summary(patient_id=patient_id),),
        visits=(make_visit_summary(patient_id=patient_id),),
        clinical_notes=(note,),
        soap_notes=(make_soap_note_summary(clinical_note_id=note.clinical_note_id),),
        lab_results=(make_lab_result_summary(patient_id=patient_id),),
        timeline_events=(make_timeline_event(patient_id=patient_id),),
    )


class TestBuildVariables:
    def test_includes_patient_demographics(self) -> None:
        builder = PromptBuilder(ai_gateway=FakeAIGateway())
        context = _empty_context()

        variables = builder.build_variables(context)

        expected_name = f"{context.patient.first_name} {context.patient.last_name}"
        assert variables["patient_name"] == expected_name
        assert variables["patient_gender"] == context.patient.gender.value

    def test_empty_sections_use_default_messages(self) -> None:
        builder = PromptBuilder(ai_gateway=FakeAIGateway())
        context = _empty_context()

        variables = builder.build_variables(context)

        assert variables["allergies_summary"] == "No known allergies."
        assert variables["medications_summary"] == "No current medications."
        assert variables["conditions_summary"] == "No known medical conditions."
        assert variables["visits_summary"] == "No prior visits on record."
        assert variables["clinical_notes_summary"] == "No prior clinical notes on record."
        assert variables["soap_notes_summary"] == "No prior SOAP notes on record."
        assert variables["lab_results_summary"] == "No prior lab results on record."
        assert variables["timeline_summary"] == "No timeline events on record."

    def test_populated_sections_summarize_content(self) -> None:
        builder = PromptBuilder(ai_gateway=FakeAIGateway())
        context = _full_context()

        variables = builder.build_variables(context)

        assert "Penicillin" in (variables["allergies_summary"] or "")
        assert "Lisinopril" in (variables["medications_summary"] or "")
        assert "Hypertension" in (variables["conditions_summary"] or "")
        assert "Complete Blood Count" in (variables["lab_results_summary"] or "")

    def test_allergy_summary_includes_severity(self) -> None:
        builder = PromptBuilder(ai_gateway=FakeAIGateway())
        variables = builder.build_variables(_full_context())
        assert "severe" in (variables["allergies_summary"] or "")

    def test_condition_summary_includes_status(self) -> None:
        builder = PromptBuilder(ai_gateway=FakeAIGateway())
        variables = builder.build_variables(_full_context())
        assert "chronic" in (variables["conditions_summary"] or "")

    def test_soap_notes_summary_includes_assessment(self) -> None:
        builder = PromptBuilder(ai_gateway=FakeAIGateway())
        variables = builder.build_variables(_full_context())
        assert "Tension headache" in (variables["soap_notes_summary"] or "")

    def test_timeline_summary_includes_event_title(self) -> None:
        builder = PromptBuilder(ai_gateway=FakeAIGateway())
        variables = builder.build_variables(_full_context())
        assert "Visit completed" in (variables["timeline_summary"] or "")

    def test_visits_summary_includes_reason_for_visit(self) -> None:
        builder = PromptBuilder(ai_gateway=FakeAIGateway())
        variables = builder.build_variables(_full_context())
        assert "Annual checkup" in (variables["visits_summary"] or "")

    def test_clinical_notes_summary_includes_assessment(self) -> None:
        builder = PromptBuilder(ai_gateway=FakeAIGateway())
        variables = builder.build_variables(_full_context())
        assert "Stable, no acute findings." in (variables["clinical_notes_summary"] or "")

    def test_extra_variables_are_merged_in(self) -> None:
        builder = PromptBuilder(ai_gateway=FakeAIGateway())
        context = _empty_context()

        variables = builder.build_variables(context, extra={"tone": "concise"})

        assert variables["tone"] == "concise"

    def test_extra_variables_override_auto_derived_ones(self) -> None:
        builder = PromptBuilder(ai_gateway=FakeAIGateway())
        context = _empty_context()

        variables = builder.build_variables(context, extra={"patient_name": "Custom Name"})

        assert variables["patient_name"] == "Custom Name"


class TestBuildMessages:
    async def test_renders_system_developer_and_user_templates(self) -> None:
        gateway = FakeAIGateway(
            rendered_prompts={
                "generic.system": "system text",
                "generic.developer": "developer text",
                "generic.user": "user text",
            }
        )
        builder = PromptBuilder(ai_gateway=gateway)
        variables = builder.build_variables(_empty_context())

        messages = await builder.build_messages(
            request_type="generic", prompt_version=1, variables=variables
        )

        assert len(messages) == 3
        assert messages[0].role is AIMessageRole.SYSTEM
        assert messages[0].content == "system text"
        assert messages[1].role is AIMessageRole.SYSTEM
        assert messages[1].content == "developer text"
        assert messages[2].role is AIMessageRole.USER
        assert messages[2].content == "user text"

    async def test_renders_the_correct_template_names_at_the_pinned_version(self) -> None:
        gateway = FakeAIGateway()
        builder = PromptBuilder(ai_gateway=gateway)
        variables = builder.build_variables(_empty_context())

        await builder.build_messages(
            request_type="soap_note", prompt_version=3, variables=variables
        )

        assert gateway.rendered_calls == [
            ("soap_note.system", 3),
            ("soap_note.developer", 3),
            ("soap_note.user", 3),
        ]

    async def test_propagates_render_prompt_errors(self) -> None:
        gateway = FakeAIGateway()

        class _BoomError(Exception):
            pass

        async def _raise(*args: object, **kwargs: object) -> str:
            raise _BoomError("template not registered")

        gateway.render_prompt = _raise  # type: ignore[method-assign]
        builder = PromptBuilder(ai_gateway=gateway)

        with pytest.raises(_BoomError):
            await builder.build_messages(
                request_type="generic",
                prompt_version=1,
                variables=builder.build_variables(_empty_context()),
            )

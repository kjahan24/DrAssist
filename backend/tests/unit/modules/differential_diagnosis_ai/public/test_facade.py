"""Unit tests for `DifferentialDiagnosisAIFacade` — exercised through
`DifferentialDiagnosisAIPort` exactly as a future consumer module would
call it, per
`docs/backend-architecture/12_testing_architecture.md`'s "Contract
tests" framing."""

from uuid import uuid4

from app.modules.differential_diagnosis_ai.application.services.clinical_reasoning_service import (
    ClinicalReasoningService,
)
from app.modules.differential_diagnosis_ai.application.services.differential_diagnosis_ranking_service import (  # noqa: E501
    DifferentialDiagnosisRankingService,
)
from app.modules.differential_diagnosis_ai.application.services.differential_diagnosis_renderer import (  # noqa: E501
    DifferentialDiagnosisRenderer,
)
from app.modules.differential_diagnosis_ai.application.use_cases.generate_differential_diagnosis import (  # noqa: E501
    GenerateDifferentialDiagnosisUseCase,
)
from app.modules.differential_diagnosis_ai.application.use_cases.rank_differential_diagnosis import (  # noqa: E501
    RankDifferentialDiagnosisUseCase,
)
from app.modules.differential_diagnosis_ai.application.use_cases.validate_clinical_evidence import (  # noqa: E501
    ValidateClinicalEvidenceUseCase,
)
from app.modules.differential_diagnosis_ai.domain.enums import (
    ClinicalSetting,
    DifferentialOutputFormat,
    UrgencyLevel,
)
from app.modules.differential_diagnosis_ai.public.dto import DifferentialDiagnosisInput
from app.modules.differential_diagnosis_ai.public.facade import DifferentialDiagnosisAIFacade
from app.modules.differential_diagnosis_ai.public.interfaces import DifferentialDiagnosisAIPort
from tests.unit.modules.differential_diagnosis_ai.application.fakes import (
    FakeClinicalReasoningPort,
    FakeDifferentialDiagnosisAuditLoggerPort,
    FakeDifferentialDiagnosisGeneratorPort,
    FakeDifferentialDiagnosisParserPort,
    FakeDifferentialDiagnosisValidatorPort,
    make_candidate,
    make_result,
)


def _evidence(**overrides: object) -> DifferentialDiagnosisInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Chest pain",
        "clinical_setting": ClinicalSetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return DifferentialDiagnosisInput(**defaults)  # type: ignore[arg-type]


def _facade(
    *, generator: FakeDifferentialDiagnosisGeneratorPort | None = None
) -> DifferentialDiagnosisAIFacade:
    generator = generator or FakeDifferentialDiagnosisGeneratorPort()
    reasoning_service = ClinicalReasoningService(reasoning=FakeClinicalReasoningPort())
    ranking_service = DifferentialDiagnosisRankingService()
    generate_use_case = GenerateDifferentialDiagnosisUseCase(
        generator=generator,
        parser=FakeDifferentialDiagnosisParserPort(result=make_result()),
        validator=FakeDifferentialDiagnosisValidatorPort(),
        reasoning_service=reasoning_service,
        ranking_service=ranking_service,
        audit_logger=FakeDifferentialDiagnosisAuditLoggerPort(),
    )
    return DifferentialDiagnosisAIFacade(
        generate_use_case=generate_use_case,
        rank_use_case=RankDifferentialDiagnosisUseCase(ranking_service=ranking_service),
        validate_use_case=ValidateClinicalEvidenceUseCase(reasoning_service=reasoning_service),
        renderer=DifferentialDiagnosisRenderer(),
        generator=generator,
    )


class TestDifferentialDiagnosisAIFacade:
    def test_is_a_differential_diagnosis_ai_port(self) -> None:
        assert isinstance(_facade(), DifferentialDiagnosisAIPort)

    async def test_generate_differential_diagnosis_delegates_to_the_use_case(self) -> None:
        facade = _facade()

        result = await facade.generate_differential_diagnosis(_evidence())

        assert result.result is not None
        assert result.session is not None

    async def test_stream_generate_differential_diagnosis_delegates_to_the_generator(
        self,
    ) -> None:
        generator = FakeDifferentialDiagnosisGeneratorPort(raw_text="hello world")
        facade = _facade(generator=generator)

        chunks = [
            chunk async for chunk in facade.stream_generate_differential_diagnosis(_evidence())
        ]

        assert "".join(c.delta for c in chunks) == "hello world"

    async def test_rank_result_delegates_to_the_ranking_service(self) -> None:
        facade = _facade()
        result = make_result(
            candidates=(
                make_candidate(disease_name="Bronchitis", confidence_score=0.2),
                make_candidate(disease_name="Pneumonia", confidence_score=0.9),
            )
        )

        ranked = await facade.rank_result(result)

        assert ranked.candidates[0].disease_name == "Pneumonia"

    async def test_render_result_delegates_to_the_renderer(self) -> None:
        facade = _facade()
        result = make_result()

        rendered = await facade.render_result(result, target_format=DifferentialOutputFormat.TEXT)

        assert "CLINICAL REASONING:" in rendered

    async def test_validate_evidence_delegates_to_the_use_case(self) -> None:
        facade = _facade()

        result = await facade.validate_evidence(_evidence())

        assert result.is_valid is True


class TestFacadeRankingIntegration:
    async def test_ranked_top_candidate_matches_urgency_tiebreak(self) -> None:
        facade = _facade()
        result = make_result(
            candidates=(
                make_candidate(
                    disease_name="Bronchitis",
                    confidence_score=0.5,
                    urgency_level=UrgencyLevel.ROUTINE,
                ),
                make_candidate(
                    disease_name="Pulmonary Embolism",
                    confidence_score=0.5,
                    urgency_level=UrgencyLevel.EMERGENT,
                ),
            )
        )

        ranked = await facade.rank_result(result)

        assert ranked.candidates[0].disease_name == "Pulmonary Embolism"

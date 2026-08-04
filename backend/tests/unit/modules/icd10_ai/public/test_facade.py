"""Unit tests for `ICD10AIFacade` — exercised through `ICD10AIPort`
exactly as a future consumer module would call it, per
`docs/backend-architecture/12_testing_architecture.md`'s "Contract
tests" framing."""

from uuid import uuid4

from app.modules.icd10_ai.application.services.icd10_ranking_service import ICD10RankingService
from app.modules.icd10_ai.application.services.icd10_suggestion_renderer import (
    ICD10SuggestionRenderer,
)
from app.modules.icd10_ai.application.use_cases.generate_icd10_suggestions import (
    GenerateICD10SuggestionsUseCase,
)
from app.modules.icd10_ai.application.use_cases.rank_icd10_suggestions import (
    RankICD10SuggestionsUseCase,
)
from app.modules.icd10_ai.application.use_cases.validate_clinical_context import (
    ValidateClinicalContextUseCase,
)
from app.modules.icd10_ai.domain.enums import CodingSetting, DiagnosisFlag, ICD10OutputFormat
from app.modules.icd10_ai.public.dto import ICD10CodingInput
from app.modules.icd10_ai.public.facade import ICD10AIFacade
from app.modules.icd10_ai.public.interfaces import ICD10AIPort
from tests.unit.modules.icd10_ai.application.fakes import (
    FakeICD10AuditLoggerPort,
    FakeICD10GeneratorPort,
    FakeICD10KnowledgePort,
    FakeICD10SuggestionParserPort,
    FakeICD10SuggestionValidatorPort,
    make_suggestion,
    make_suggestion_set,
)


def _coding_input(**overrides: object) -> ICD10CodingInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_id": uuid4(),
        "chief_complaint": "Sore throat",
        "coding_setting": CodingSetting.OUTPATIENT,
    }
    defaults.update(overrides)
    return ICD10CodingInput(**defaults)  # type: ignore[arg-type]


def _facade(*, generator: FakeICD10GeneratorPort | None = None) -> ICD10AIFacade:
    generator = generator or FakeICD10GeneratorPort()
    ranking_service = ICD10RankingService(knowledge=FakeICD10KnowledgePort())
    generate_use_case = GenerateICD10SuggestionsUseCase(
        generator=generator,
        parser=FakeICD10SuggestionParserPort(result=make_suggestion_set()),
        validator=FakeICD10SuggestionValidatorPort(),
        ranking_service=ranking_service,
        audit_logger=FakeICD10AuditLoggerPort(),
    )
    return ICD10AIFacade(
        generate_use_case=generate_use_case,
        validate_use_case=ValidateClinicalContextUseCase(),
        rank_use_case=RankICD10SuggestionsUseCase(ranking_service=ranking_service),
        renderer=ICD10SuggestionRenderer(),
        generator=generator,
    )


class TestICD10AIFacade:
    def test_is_an_icd10_ai_port(self) -> None:
        assert isinstance(_facade(), ICD10AIPort)

    async def test_generate_suggestions_delegates_to_the_use_case(self) -> None:
        facade = _facade()

        result = await facade.generate_suggestions(_coding_input())

        assert result.suggestions is not None
        assert result.session is not None

    async def test_stream_generate_suggestions_delegates_to_the_generator(self) -> None:
        generator = FakeICD10GeneratorPort(raw_text="hello world")
        facade = _facade(generator=generator)

        chunks = [chunk async for chunk in facade.stream_generate_suggestions(_coding_input())]

        assert "".join(c.delta for c in chunks) == "hello world"

    async def test_rank_suggestions_delegates_to_the_ranking_service(self) -> None:
        facade = _facade()
        suggestion_set = make_suggestion_set(
            suggestions=(
                make_suggestion(icd10_code="A00", flag=DiagnosisFlag.SECONDARY),
                make_suggestion(icd10_code="B00", flag=DiagnosisFlag.PRIMARY),
            )
        )

        ranked = await facade.rank_suggestions(suggestion_set)

        assert ranked.suggestions[0].flag is DiagnosisFlag.PRIMARY

    async def test_render_suggestions_delegates_to_the_renderer(self) -> None:
        facade = _facade()
        suggestion_set = make_suggestion_set()

        rendered = await facade.render_suggestions(
            suggestion_set, target_format=ICD10OutputFormat.TEXT
        )

        assert "CLINICAL REASONING:" in rendered

    async def test_validate_context_delegates_to_the_use_case(self) -> None:
        facade = _facade()

        result = await facade.validate_context(_coding_input())

        assert result.is_valid is True

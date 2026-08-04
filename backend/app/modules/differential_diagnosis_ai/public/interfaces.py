"""The AI Differential Diagnosis module's public port — the only
contract another module may depend on
(`docs/backend-architecture/03_module_architecture.md`,
`10_module_communication.md`).

Never import from `app.modules.differential_diagnosis_ai.domain`,
`.application` (beyond this package's own re-exports in `public/dto.py`),
or `.infrastructure` from outside this module. The pre-existing
`app.modules.differential_diagnosis` module (structured, persisted
differential diagnosis records — a completed backend module, not
modified by this task) is the expected future consumer of this one's
`generate_differential_diagnosis`: it lets a physician review a ranked
AI-drafted differential before persisting a `DiagnosisSource.AI`/
`DiagnosisSource.HYBRID` record — this module itself never creates a
final diagnosis or replaces physician judgment, per this task's own "It
NEVER creates a final diagnosis. It NEVER replaces physician judgment.
All outputs are clinical decision-support only" scope.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.modules.differential_diagnosis_ai.public.dto import (
    ClinicalEvidenceValidationResultDTO,
    DifferentialDiagnosisInput,
    DifferentialDiagnosisResult,
    DifferentialDiagnosisStreamChunk,
    DifferentialOutputFormat,
    GeneratedDifferentialDiagnosis,
)


class DifferentialDiagnosisAIPort(ABC):
    @abstractmethod
    async def generate_differential_diagnosis(
        self, evidence: DifferentialDiagnosisInput
    ) -> GeneratedDifferentialDiagnosis: ...

    @abstractmethod
    def stream_generate_differential_diagnosis(
        self, evidence: DifferentialDiagnosisInput
    ) -> AsyncIterator[DifferentialDiagnosisStreamChunk]: ...

    @abstractmethod
    async def rank_result(
        self, result: DifferentialDiagnosisResult
    ) -> DifferentialDiagnosisResult: ...

    @abstractmethod
    async def render_result(
        self, result: DifferentialDiagnosisResult, *, target_format: DifferentialOutputFormat
    ) -> str: ...

    @abstractmethod
    async def validate_evidence(
        self, evidence: DifferentialDiagnosisInput
    ) -> ClinicalEvidenceValidationResultDTO: ...

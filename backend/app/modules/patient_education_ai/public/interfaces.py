"""The AI Patient Education & Discharge Instructions module's public
port — the only contract another module may depend on
(`docs/backend-architecture/03_module_architecture.md`,
`10_module_communication.md`).

Never import from `app.modules.patient_education_ai.domain`,
`.application` (beyond this package's own re-exports in `public/dto.py`),
or `.infrastructure` from outside this module.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from app.modules.patient_education_ai.public.dto import (
    GeneratedPatientEducation,
    PatientEducationInput,
    PatientEducationOutputFormat,
    PatientEducationResult,
    PatientEducationStreamChunk,
)


class PatientEducationAIPort(ABC):
    @abstractmethod
    async def generate_patient_education(
        self, input_dto: PatientEducationInput
    ) -> GeneratedPatientEducation: ...

    @abstractmethod
    def stream_generate_patient_education(
        self, input_dto: PatientEducationInput
    ) -> AsyncIterator[PatientEducationStreamChunk]: ...

    @abstractmethod
    async def render_result(
        self,
        result: PatientEducationResult,
        *,
        target_format: PatientEducationOutputFormat,
    ) -> str: ...

"""FastAPI dependency providers for the AI Clinical Note Generation
module.

`get_clinical_note_ai_facade` is provided now, ahead of any real endpoint
using it, so a future consumer can `Depends()` on it immediately — the
same "structure only" pattern
`app.modules.ai_copilot.api.dependencies` already establishes for itself.
No `AsyncSession` dependency: this module owns no database session (see
`container.py`'s own scope note).
"""

from typing import Annotated

from fastapi import Depends

from app.modules.clinical_note_ai.container import get_clinical_note_ai_facade
from app.modules.clinical_note_ai.public.facade import ClinicalNoteAIFacade

ClinicalNoteAIFacadeDep = Annotated[ClinicalNoteAIFacade, Depends(get_clinical_note_ai_facade)]

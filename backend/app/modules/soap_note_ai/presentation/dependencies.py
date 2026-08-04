"""FastAPI dependency providers for the AI SOAP Note Generation module.

`get_soap_note_ai_facade` is provided now, ahead of any real endpoint
using it, the same "structure only" pattern
`app.modules.clinical_note_ai.presentation.dependencies` already
establishes for itself. No `AsyncSession` dependency: this module owns no
database session (see `container.py`'s own scope note).
"""

from typing import Annotated

from fastapi import Depends

from app.modules.soap_note_ai.container import get_soap_note_ai_facade
from app.modules.soap_note_ai.public.facade import SOAPNoteAIFacade

SOAPNoteAIFacadeDep = Annotated[SOAPNoteAIFacade, Depends(get_soap_note_ai_facade)]

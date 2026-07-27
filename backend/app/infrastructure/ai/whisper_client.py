"""faster-whisper adapter skeleton.

Implements `SpeechToTextPort`. Model loading configuration only — no
transcription pipeline logic lives here yet.
"""

from functools import lru_cache

from faster_whisper import WhisperModel

from app.core.config import get_settings
from app.shared.application.ai_provider_port import SpeechToTextPort


class WhisperClient(SpeechToTextPort):
    def __init__(self, model_size: str, device: str, compute_type: str) -> None:
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._model: WhisperModel | None = None

    async def transcribe(self, *, audio_bytes: bytes, language: str | None = None) -> str:
        raise NotImplementedError


@lru_cache
def get_whisper_client() -> WhisperClient:
    settings = get_settings()
    return WhisperClient(
        model_size=settings.whisper.model_size,
        device=settings.whisper.device,
        compute_type=settings.whisper.compute_type,
    )

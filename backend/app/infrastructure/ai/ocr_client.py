"""PaddleOCR adapter skeleton.

Implements `OCRPort`. Engine configuration only — no extraction pipeline
logic lives here yet.
"""

from functools import lru_cache

from paddleocr import PaddleOCR

from app.core.config import get_settings
from app.shared.application.ai_provider_port import OCRPort


class PaddleOCRClient(OCRPort):
    def __init__(self, lang: str, use_gpu: bool) -> None:
        self._lang = lang
        self._use_gpu = use_gpu
        self._engine: PaddleOCR | None = None

    async def extract_text(self, *, image_bytes: bytes) -> str:
        raise NotImplementedError


@lru_cache
def get_ocr_client() -> PaddleOCRClient:
    settings = get_settings()
    return PaddleOCRClient(lang=settings.paddleocr.lang, use_gpu=settings.paddleocr.use_gpu)

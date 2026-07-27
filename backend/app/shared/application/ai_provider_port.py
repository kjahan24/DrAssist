"""Ports for AI capabilities.

Method signatures only — no prompt content, model-specific request
shaping, or business rules. Implementations live in
`app/infrastructure/ai/` (Gemini, faster-whisper, PaddleOCR).
"""

from abc import ABC, abstractmethod


class TextGenerationPort(ABC):
    @abstractmethod
    async def generate(self, *, prompt: str, **kwargs: object) -> str: ...


class SpeechToTextPort(ABC):
    @abstractmethod
    async def transcribe(self, *, audio_bytes: bytes, language: str | None = None) -> str: ...


class OCRPort(ABC):
    @abstractmethod
    async def extract_text(self, *, image_bytes: bytes) -> str: ...

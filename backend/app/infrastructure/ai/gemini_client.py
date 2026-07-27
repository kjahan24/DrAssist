"""Gemini adapter skeleton.

Implements `TextGenerationPort`. Client construction and configuration
only — no prompt templates or generation logic live here; those belong to
whichever use case consumes this port once defined.
"""

from functools import lru_cache

import google.generativeai as genai

from app.application.interfaces.ai_provider_port import TextGenerationPort
from app.core.config import get_settings


class GeminiClient(TextGenerationPort):
    def __init__(self, api_key: str, model_name: str) -> None:
        genai.configure(api_key=api_key)
        self._model_name = model_name
        self._model: genai.GenerativeModel | None = None

    async def generate(self, *, prompt: str, **kwargs: object) -> str:
        raise NotImplementedError


@lru_cache
def get_gemini_client() -> GeminiClient:
    settings = get_settings()
    return GeminiClient(api_key=settings.gemini.api_key, model_name=settings.gemini.model)

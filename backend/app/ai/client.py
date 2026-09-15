"""
AI Client Wrapper — using google-genai SDK for Gemini 2.0 Flash.

Provides a configured client for structured outputs and text generation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Type, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.core.config import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class AIClient:
    """Wrapper around google-genai Client."""

    def __init__(self) -> None:
        settings = get_settings()
        self.model_name = settings.AI_MODEL
        if not settings.AI_API_KEY:
            logger.warning("AI_API_KEY is not set. AI validation/generation will fail.")
        
        self.client = genai.Client(api_key=settings.AI_API_KEY)

    def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        temperature: float = 0.0,
    ) -> T:
        """
        Generate a structured JSON response matching the given Pydantic schema.
        Uses temperature 0.0 by default for deterministic validation.
        """
        try:
            logger.info("Calling Gemini API (%s) for structured output...", self.model_name)
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    temperature=temperature,
                ),
            )
            
            # The SDK parses the JSON into the pydantic model for us if we access .parsed
            if hasattr(response, "parsed") and response.parsed is not None:
                return response.parsed
                
            # Fallback if parsed is not populated (e.g. older SDK or beta mismatch)
            return response_schema.model_validate_json(response.text)
            
        except Exception as e:
            logger.error("Gemini API call failed: %s", str(e))
            raise

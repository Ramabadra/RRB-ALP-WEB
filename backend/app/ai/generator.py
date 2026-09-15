"""
AI Generator — handles generating new questions via Gemini.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from app.ai.client import AIClient
from app.ai.prompts import (
    GENERATION_PROMPT_TEMPLATE,
    GeneratedQuestion,
    GeneratedQuestionsBatchSchema,
)

logger = logging.getLogger(__name__)


class AIGenerator:
    def __init__(self, client: Optional[AIClient] = None) -> None:
        self.client = client or AIClient()

    def generate_questions(
        self,
        subject: str,
        topic: str,
        difficulty: str,
        count: int = 5,
    ) -> List[GeneratedQuestion]:
        """
        Generates `count` new questions for the given subject/topic/difficulty.
        """
        prompt = GENERATION_PROMPT_TEMPLATE.format(
            count=count,
            subject=subject,
            topic=topic,
            difficulty=difficulty,
        )

        logger.info("Generating %d %s questions for topic %s...", count, difficulty, topic)
        result: GeneratedQuestionsBatchSchema = self.client.generate_structured(
            prompt=prompt,
            response_schema=GeneratedQuestionsBatchSchema,
            temperature=0.7,  # Higher temperature for generation variety
        )
        return result.questions

"""
AI Validator — handles validating individual questions via Gemini.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.ai.client import AIClient
from app.ai.prompts import VALIDATION_PROMPT_TEMPLATE, ValidatedQuestionSchema
from app.models.question import Question

logger = logging.getLogger(__name__)


class AIValidator:
    def __init__(self, client: Optional[AIClient] = None) -> None:
        self.client = client or AIClient()

    def validate_question(self, question: Question) -> ValidatedQuestionSchema:
        """
        Takes a DB Question object (typically from OCR) and sends it to the AI for validation.
        Returns a ValidatedQuestionSchema.
        """
        prompt = VALIDATION_PROMPT_TEMPLATE.format(
            question_text=question.question_text,
            option_a=question.option_a,
            option_b=question.option_b,
            option_c=question.option_c,
            option_d=question.option_d,
            extracted_answer=question.correct_answer or "None extracted",
        )

        logger.info("Validating question ID %s via AI...", question.id)
        result: ValidatedQuestionSchema = self.client.generate_structured(
            prompt=prompt,
            response_schema=ValidatedQuestionSchema,
            temperature=0.0,  # Deterministic validation
        )
        return result

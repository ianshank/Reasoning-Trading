"""
LLM-based sentiment analyzer implementation.

Uses OpenAI or Anthropic models for sophisticated sentiment analysis
with reasoning capabilities.
"""

from __future__ import annotations

import json
import time
from typing import Any

import structlog

from reasoning_trading.config import Settings, get_settings
from reasoning_trading.sentiment.analyzers.base import (
    AnalyzerError,
    BaseSentimentAnalyzer,
)
from reasoning_trading.sentiment.models import SentimentLabel, SentimentScore

logger = structlog.get_logger(__name__)


# Prompt template for sentiment analysis
SENTIMENT_PROMPT = """Analyze the sentiment of the following financial news text and provide a JSON response.

Text: {text}

Analyze this text for financial/market sentiment. Consider:
- Overall tone (bullish, bearish, or neutral)
- Confidence in the sentiment assessment
- Key factors driving the sentiment

Respond with ONLY a valid JSON object in this exact format:
{{
    "sentiment": "bullish" | "bearish" | "neutral",
    "score": <float between -1 and 1, where -1 is most bearish and 1 is most bullish>,
    "confidence": <float between 0 and 1>,
    "reasoning": "<brief explanation>"
}}"""


class LLMSentimentAnalyzer(BaseSentimentAnalyzer):
    """
    LLM-based sentiment analyzer.

    Uses language models (OpenAI, Anthropic) for nuanced
    sentiment analysis with reasoning.
    """

    MAX_TEXT_LENGTH = 2000  # Limit to save tokens

    def __init__(
        self,
        settings: Settings | None = None,
        model: str | None = None,
    ):
        """
        Initialize LLM analyzer.

        Args:
            settings: Application settings
            model: Override model name (defaults to quick_think_llm)
        """
        self._settings = settings or get_settings()
        self._model = model or self._settings.llm.quick_think_llm
        self._client: Any = None
        self._available: bool | None = None

    @property
    def name(self) -> str:
        """Get analyzer name."""
        return "LLM"

    @property
    def model_name(self) -> str:
        """Get the underlying model name."""
        return self._model

    def is_available(self) -> bool:
        """Check if LLM API is available."""
        if self._available is not None:
            return self._available

        # Check for OpenAI or Anthropic key
        has_openai = self._settings.llm.openai_api_key is not None
        has_anthropic = self._settings.llm.anthropic_api_key is not None

        self._available = has_openai or has_anthropic

        if self._available:
            logger.debug(
                "LLM analyzer available",
                provider="openai" if has_openai else "anthropic",
            )
        else:
            logger.warning("LLM analyzer not available - no API key configured")

        return self._available

    async def _get_client(self) -> Any:
        """Get or create the LLM client."""
        if self._client is None:
            if not self.is_available():
                raise AnalyzerError(
                    message="LLM not available - no API key configured",
                    analyzer=self.name,
                    retriable=False,
                )

            # Prefer OpenAI
            if self._settings.llm.openai_api_key is not None:
                try:
                    from langchain_openai import ChatOpenAI

                    self._client = ChatOpenAI(
                        model=self._model,
                        api_key=self._settings.llm.openai_api_key.get_secret_value(),
                        temperature=0.1,  # Low temperature for consistency
                    )
                    logger.debug("Using OpenAI for LLM sentiment analysis")
                except ImportError:
                    raise AnalyzerError(
                        message="langchain-openai not installed",
                        analyzer=self.name,
                        retriable=False,
                    )
            elif self._settings.llm.anthropic_api_key is not None:
                try:
                    from langchain_anthropic import ChatAnthropic

                    self._client = ChatAnthropic(
                        model="claude-3-haiku-20240307",  # Fast model for sentiment
                        api_key=self._settings.llm.anthropic_api_key.get_secret_value(),
                        temperature=0.1,
                    )
                    logger.debug("Using Anthropic for LLM sentiment analysis")
                except ImportError:
                    raise AnalyzerError(
                        message="langchain-anthropic not installed",
                        analyzer=self.name,
                        retriable=False,
                    )

        return self._client

    async def analyze(self, text: str) -> SentimentScore:
        """
        Analyze sentiment using LLM.

        Args:
            text: Text to analyze

        Returns:
            SentimentScore with results
        """
        if not text.strip():
            return SentimentScore.from_probabilities(
                positive=0.0,
                negative=0.0,
                neutral=1.0,
                model_name=self.model_name,
            )

        start_time = time.perf_counter()

        try:
            client = await self._get_client()

            # Truncate text
            truncated = self._truncate_text(text, self.MAX_TEXT_LENGTH)

            # Format prompt
            prompt = SENTIMENT_PROMPT.format(text=truncated)

            # Call LLM
            response = await client.ainvoke(prompt)
            response_text = response.content

            # Parse JSON response
            result = self._parse_response(response_text)

            processing_time = (time.perf_counter() - start_time) * 1000
            result.processing_time_ms = processing_time

            logger.debug(
                "LLM analysis complete",
                score=result.score,
                label=result.label,
                processing_time_ms=processing_time,
            )

            return result

        except AnalyzerError:
            raise
        except Exception as e:
            raise AnalyzerError(
                message=f"LLM analysis failed: {str(e)}",
                analyzer=self.name,
                retriable=True,
                original_error=e,
            )

    def _parse_response(self, response_text: str) -> SentimentScore:
        """Parse the LLM JSON response into a SentimentScore."""
        try:
            # Try to extract JSON from response
            # Handle cases where model wraps JSON in markdown
            text = response_text.strip()
            if text.startswith("```"):
                # Remove markdown code blocks
                lines = text.split("\n")
                json_lines = [
                    l for l in lines if not l.startswith("```")
                ]
                text = "\n".join(json_lines)

            data = json.loads(text)

            # Extract values with defaults
            sentiment = data.get("sentiment", "neutral").lower()
            score = float(data.get("score", 0.0))
            confidence = float(data.get("confidence", 0.5))

            # Map sentiment to label
            if sentiment == "bullish" or sentiment == "positive":
                label = SentimentLabel.BULLISH
            elif sentiment == "bearish" or sentiment == "negative":
                label = SentimentLabel.BEARISH
            else:
                label = SentimentLabel.NEUTRAL

            # Clamp values to valid ranges
            score = max(-1.0, min(1.0, score))
            confidence = max(0.0, min(1.0, confidence))

            # Calculate probabilities from score
            if score > 0:
                positive = (score + 1) / 2
                negative = 0.1 * (1 - positive)
                neutral = 1 - positive - negative
            elif score < 0:
                negative = (-score + 1) / 2
                positive = 0.1 * (1 - negative)
                neutral = 1 - positive - negative
            else:
                positive = 0.2
                negative = 0.2
                neutral = 0.6

            return SentimentScore(
                score=score,
                confidence=confidence,
                label=label,
                model_name=self.model_name,
                probabilities={
                    "positive": positive,
                    "negative": negative,
                    "neutral": neutral,
                },
            )

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(
                "Failed to parse LLM response",
                response=response_text[:200],
                error=str(e),
            )
            # Return neutral on parse failure
            return SentimentScore.from_probabilities(
                positive=0.33,
                negative=0.33,
                neutral=0.34,
                model_name=self.model_name,
            )

    async def analyze_batch(self, texts: list[str]) -> list[SentimentScore]:
        """
        Batch analyze multiple texts.

        LLM calls are expensive, so we process sequentially
        with some concurrency.
        """
        import asyncio

        # Process in small batches to balance speed and cost
        batch_size = 5
        results = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_results = await asyncio.gather(
                *[self.analyze(text) for text in batch],
                return_exceptions=True,
            )

            for result in batch_results:
                if isinstance(result, Exception):
                    # Return neutral on failure
                    results.append(
                        SentimentScore.from_probabilities(
                            positive=0.33,
                            negative=0.33,
                            neutral=0.34,
                            model_name=self.model_name,
                        )
                    )
                else:
                    results.append(result)

        return results

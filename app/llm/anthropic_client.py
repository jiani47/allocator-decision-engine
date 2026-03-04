"""Anthropic API wrapper with retries."""

from __future__ import annotations

import logging
from collections.abc import Generator

from anthropic import Anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import Settings

logger = logging.getLogger("equi.llm")


class AnthropicClient:
    def __init__(self, settings: Settings, api_key_override: str | None = None) -> None:
        api_key = api_key_override or settings.anthropic_api_key
        self._client = Anthropic(api_key=api_key)
        self._model = settings.anthropic_model
        self._max_tokens = settings.anthropic_max_tokens
        self._temperature = settings.anthropic_temperature

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def generate(self, prompt: str, system_prompt: str) -> str:
        """Send prompt to Claude, return raw text response."""
        logger.info("Calling Anthropic model=%s", self._model)
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text
        logger.info("Received response: %d chars", len(raw))
        return raw

    def generate_stream(
        self, prompt: str, system_prompt: str
    ) -> Generator[str, None, None]:
        """Stream tokens from Claude, yielding text chunks."""
        logger.info("Streaming from Anthropic model=%s", self._model)
        with self._client.messages.stream(
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                yield text

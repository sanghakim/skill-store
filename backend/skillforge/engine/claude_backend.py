"""
Claude LLM Backend - Real Anthropic Claude API integration.

Implements the LLMBackend protocol to replace SimulatedLLMBackend.
Supports Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku, etc.

Usage:
    backend = ClaudeLLMBackend(api_key="sk-ant-...")
    result = backend.generate(prompt, max_tokens=2000, temperature=0.7)

Environment:
    ANTHROPIC_API_KEY - API key (required if not passed to constructor)
    CLAUDE_MODEL      - Model name (default: claude-sonnet-4-20250514)
    CLAUDE_MAX_RETRIES - Max retry attempts (default: 2)
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

# Default model - can be overridden via env var or constructor
DEFAULT_MODEL = "claude-sonnet-4-20250514"


class ClaudeLLMBackend:
    """
    Real Claude API backend implementing the LLMBackend Protocol.

    Conforms to the sync interface:
        def generate(self, prompt: str, max_tokens: int, temperature: float) -> str
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_retries: int | None = None,
        system_prompt: str | None = None,
    ):
        # Resolve configuration from constructor args → env vars → defaults
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self._model = model or os.getenv("CLAUDE_MODEL", DEFAULT_MODEL)
        self._max_retries = max_retries or int(os.getenv("CLAUDE_MAX_RETRIES", "2"))
        self._system_prompt = system_prompt or (
            "You are a professional AI assistant specialized in Korean office productivity. "
            "Always respond in the same language as the prompt. "
            "Provide detailed, well-structured, and actionable responses."
        )

        if not self._api_key:
            raise ValueError(
                "Anthropic API key is required. "
                "Set ANTHROPIC_API_KEY environment variable or pass api_key to constructor."
            )

        # Initialize Anthropic client
        self._client = anthropic.Anthropic(
            api_key=self._api_key,
            max_retries=self._max_retries,
        )

        logger.info(
            "ClaudeLLMBackend initialized: model=%s, max_retries=%d",
            self._model,
            self._max_retries,
        )

    def generate(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> str:
        """
        Generate a response from Claude API.

        This is the core method matching the LLMBackend protocol.
        Sends the prompt as a user message and returns the assistant's text.

        Args:
            prompt: The fully resolved prompt (with template variables replaced)
            max_tokens: Maximum tokens for the response
            temperature: Sampling temperature (0.0-1.0 for Claude)

        Returns:
            The generated text response
        """
        start_time = time.time()

        # Claude API caps temperature at 1.0
        clamped_temp = min(temperature, 1.0)

        try:
            message = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                temperature=clamped_temp,
                system=self._system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ],
            )

            # Extract text from response
            response_text = ""
            for block in message.content:
                if block.type == "text":
                    response_text += block.text

            elapsed_ms = int((time.time() - start_time) * 1000)

            logger.info(
                "Claude API call: model=%s, input_tokens=%d, output_tokens=%d, time=%dms",
                message.model,
                message.usage.input_tokens,
                message.usage.output_tokens,
                elapsed_ms,
            )

            return response_text

        except anthropic.AuthenticationError as exc:
            logger.error("Claude API authentication failed: %s", exc)
            raise ValueError(f"Invalid Anthropic API key: {exc}") from exc

        except anthropic.RateLimitError as exc:
            logger.warning("Claude API rate limited: %s", exc)
            raise RuntimeError(f"Claude API rate limit exceeded: {exc}") from exc

        except anthropic.APIStatusError as exc:
            logger.error("Claude API error [%d]: %s", exc.status_code, exc.message)
            raise RuntimeError(f"Claude API error: {exc.message}") from exc

        except Exception as exc:
            logger.error("Unexpected Claude API error: %s", exc)
            raise RuntimeError(f"Claude API call failed: {exc}") from exc

    def generate_with_metadata(
        self,
        prompt: str,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """
        Extended generate that also returns token usage and metadata.
        Not part of the LLMBackend protocol — for diagnostic use.
        """
        clamped_temp = min(temperature, 1.0)
        start_time = time.time()

        message = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            temperature=clamped_temp,
            system=self._system_prompt,
            messages=[
                {"role": "user", "content": prompt}
            ],
        )

        response_text = ""
        for block in message.content:
            if block.type == "text":
                response_text += block.text

        elapsed_ms = int((time.time() - start_time) * 1000)

        return {
            "text": response_text,
            "model": message.model,
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
            "total_tokens": message.usage.input_tokens + message.usage.output_tokens,
            "stop_reason": message.stop_reason,
            "elapsed_ms": elapsed_ms,
        }

    @property
    def model(self) -> str:
        return self._model

    def __repr__(self) -> str:
        return f"ClaudeLLMBackend(model={self._model!r})"

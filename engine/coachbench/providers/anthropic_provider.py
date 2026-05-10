from __future__ import annotations

import json
import os

from .base import Provider, ProviderResponse


class AnthropicProvider(Provider):
    requires_network: bool = True
    name: str = "anthropic"

    DEFAULT_MODEL = "claude-sonnet-4-6"
    DEFAULT_MAX_TOKENS = 512

    def __init__(
        self,
        model: str | None = None,
        max_tokens: int | None = None,
        api_key: str | None = None,
    ) -> None:
        resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise RuntimeError(
                "AnthropicProvider requires ANTHROPIC_API_KEY in the environment "
                "or an explicit api_key argument."
            )
        import anthropic

        self._client = anthropic.Anthropic(api_key=resolved_key)
        self._model = model or os.environ.get("COACHBENCH_MODEL_NAME", self.DEFAULT_MODEL)
        self._max_tokens = int(max_tokens or self.DEFAULT_MAX_TOKENS)

    def query(self, *, system: str, user: str) -> ProviderResponse:
        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=[
                    {
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user}],
            )
            raw_text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
            parsed = self._parse_json(raw_text)
            return ProviderResponse(raw_text=raw_text, parsed_json=parsed, error=None)
        except Exception as exc:
            return ProviderResponse(raw_text="", parsed_json=None, error=f"{type(exc).__name__}: {exc}")

    @staticmethod
    def _parse_json(text: str) -> dict | None:
        text = text.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None

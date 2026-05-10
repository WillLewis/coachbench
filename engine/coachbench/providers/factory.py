from __future__ import annotations

from typing import Any

from .base import Provider
from .fake_provider import FakeProvider


def make_provider(name: str, config: dict[str, Any] | None = None) -> Provider:
    config = config or {}
    if name == "fake":
        return FakeProvider(**config)
    if name == "anthropic":
        from .anthropic_provider import AnthropicProvider
        return AnthropicProvider(**config)
    raise ValueError(f"unknown provider: {name}")

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderResponse:
    raw_text: str
    parsed_json: dict | None
    error: str | None = None


class Provider:
    requires_network: bool = False
    name: str = "abstract"

    def query(self, *, system: str, user: str) -> ProviderResponse:
        raise NotImplementedError

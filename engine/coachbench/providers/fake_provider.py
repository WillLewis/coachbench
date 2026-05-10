from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from .base import Provider, ProviderResponse


class FakeProvider(Provider):
    requires_network: bool = False
    name: str = "fake"

    def __init__(
        self,
        canned_responses: Sequence[ProviderResponse] | None = None,
        default_payload: dict[str, Any] | None = None,
    ) -> None:
        self._canned: list[ProviderResponse] = list(canned_responses or [])
        self._default_payload = default_payload
        self._call_count = 0

    def query(self, *, system: str, user: str) -> ProviderResponse:
        if self._call_count < len(self._canned):
            response = self._canned[self._call_count]
        elif self._default_payload is not None:
            text = json.dumps(self._default_payload)
            response = ProviderResponse(raw_text=text, parsed_json=dict(self._default_payload), error=None)
        else:
            response = ProviderResponse(raw_text="", parsed_json=None, error="fake provider exhausted")
        self._call_count += 1
        return response

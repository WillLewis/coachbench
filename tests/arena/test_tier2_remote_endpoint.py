from __future__ import annotations

import httpx
import pytest

from arena.tiers.base import SanitizedObservation
from arena.tiers.remote_endpoint import Tier2Adapter, Tier2Config, validate_endpoint_url


def _obs() -> SanitizedObservation:
    return SanitizedObservation("offense", {"down": 1}, ["quick_game", "screen"], {}, {"own_recent_calls": [], "opponent_visible_tendencies": {}, "beliefs": {}})


def _adapter(handler, limit: int = 60) -> Tier2Adapter:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    config = Tier2Config("Remote", "offense", "remote_endpoint", rate_limit_per_minute=limit)
    return Tier2Adapter(config, "https://example.invalid/agent", http_client=client, agent_id="a")


def test_tier2_response_modes() -> None:
    ok = _adapter(lambda request: httpx.Response(200, json={"action": "screen", "rationale": "safe rationale"}))
    assert ok.choose_action(_obs()) == "screen"
    assert ok.rationales == ["safe rationale"]

    bad_action = _adapter(lambda request: httpx.Response(200, json={"action": "bad"}))
    assert bad_action.choose_action(_obs()) == "quick_game"
    assert bad_action.fallback_reasons[-1] == "tier2_invalid_action"

    malformed = _adapter(lambda request: httpx.Response(200, content=b"{"))
    assert malformed.choose_action(_obs()) == "quick_game"
    assert malformed.fallback_reasons[-1] == "tier2_malformed_response"

    huge = _adapter(lambda request: httpx.Response(200, content=b"x" * 9000))
    assert huge.choose_action(_obs()) == "quick_game"
    assert huge.fallback_reasons[-1] == "tier2_malformed_response"

    down = _adapter(lambda request: httpx.Response(500))
    assert down.choose_action(_obs()) == "quick_game"
    assert down.fallback_reasons[-1] == "tier2_unreachable"

    timeout = _adapter(lambda request: (_ for _ in ()).throw(httpx.TimeoutException("slow")))
    assert timeout.choose_action(_obs()) == "quick_game"
    assert timeout.fallback_reasons[-1] == "tier2_timeout"


def test_tier2_url_policy_and_rate_limit() -> None:
    for url in ("http://example.invalid/agent", "https://127.0.0.1/agent", "https://10.0.0.5/agent"):
        with pytest.raises(ValueError):
            validate_endpoint_url(url)
    limited = _adapter(lambda request: httpx.Response(200, json={"action": "screen"}), limit=1)
    assert limited.choose_action(_obs()) == "screen"
    assert limited.choose_action(_obs()) == "quick_game"
    assert limited.fallback_reasons[-1] == "tier2_rate_limited"

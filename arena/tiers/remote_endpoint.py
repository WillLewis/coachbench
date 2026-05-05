from __future__ import annotations

import hashlib
import ipaddress
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from arena.api.deps import moderate
from coachbench.contracts import validate_remote_endpoint_response

ALLOWED_SCHEMES = {"https"}
DENYLISTED_NETLOCS = {"localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254", "::1"}
DENYLISTED_CIDRS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
)


def normalize_endpoint_url(url: str) -> str:
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    scheme = parsed.scheme.lower()
    path = parsed.path or "/"
    port = f":{parsed.port}" if parsed.port else ""
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{scheme}://{host}{port}{path}{query}"


def endpoint_url_hash(url: str) -> str:
    return hashlib.sha256(normalize_endpoint_url(url).encode()).hexdigest()


def validate_endpoint_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError("remote endpoints must use https")
    host = parsed.hostname or ""
    if host.lower() in DENYLISTED_NETLOCS:
        raise ValueError("remote endpoint host is not allowed")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return
    if any(ip in network for network in DENYLISTED_CIDRS):
        raise ValueError("remote endpoint private address is not allowed")


@dataclass(frozen=True)
class Tier2Config:
    agent_name: str
    side: str
    access_tier: str
    timeout_ms: int = 800
    api_key_secret_id: str | None = None
    rate_limit_per_minute: int = 60


class _RateLimiter:
    def __init__(self) -> None:
        self.calls: dict[str, list[float]] = {}

    def allow(self, key: str, limit: int) -> bool:
        now = time.monotonic()
        window = [item for item in self.calls.get(key, []) if now - item < 60]
        if len(window) >= limit:
            self.calls[key] = window
            return False
        window.append(now)
        self.calls[key] = window
        return True


class Tier2Adapter:
    access_tier = "remote_endpoint"

    def __init__(self, config: Tier2Config, endpoint_url: str, api_key: str | None = None, http_client: httpx.Client | None = None, agent_id: str = "remote") -> None:
        validate_endpoint_url(endpoint_url)
        self.config = config
        self.endpoint_url = normalize_endpoint_url(endpoint_url)
        self.endpoint_url_hash = endpoint_url_hash(endpoint_url)
        self.api_key = api_key
        self.client = http_client or httpx.Client(follow_redirects=False, timeout=min(config.timeout_ms, 2000) / 1000)
        self.agent_id = agent_id
        self.name = config.agent_name
        self.fallback_reasons: list[str] = []
        self.rationales: list[str] = []
        self._rate_limiter = _RateLimiter()

    def _fallback(self, reason: str, obs) -> str:
        self.fallback_reasons.append(reason)
        return sorted(obs.legal_actions)[0]

    def choose_action(self, obs) -> str:
        if not self._rate_limiter.allow(self.agent_id, int(self.config.rate_limit_per_minute)):
            return self._fallback("tier2_rate_limited", obs)
        payload = {
            "match_id": "local-tier2",
            "agent_id": self.agent_id,
            "side": obs.side,
            "observation": {
                "game_state": obs.game_state,
                "own_resource_remaining": obs.own_resource_remaining,
                "memory_summary": obs.memory_summary,
            },
            "legal_actions": obs.legal_actions,
            "timeout_ms": min(int(self.config.timeout_ms), 2000),
        }
        headers = {"User-Agent": "CoachBench-Arena/0.6a"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            response = self.client.post(self.endpoint_url, json=payload, headers=headers)
        except httpx.TimeoutException:
            return self._fallback("tier2_timeout", obs)
        except Exception:
            return self._fallback("tier2_unreachable", obs)
        if response.status_code < 200 or response.status_code >= 300:
            return self._fallback("tier2_unreachable", obs)
        if len(response.content) > 8 * 1024:
            return self._fallback("tier2_malformed_response", obs)
        try:
            data = response.json()
            validate_remote_endpoint_response(data)
        except Exception:
            return self._fallback("tier2_malformed_response", obs)
        if data["action"] not in obs.legal_actions:
            return self._fallback("tier2_invalid_action", obs)
        rationale = data.get("rationale")
        if rationale:
            try:
                moderate(str(rationale))
                self.rationales.append(str(rationale)[:280])
            except Exception:
                pass
        return data["action"]

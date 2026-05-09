from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass

from arena.storage import llm_budget as storage


class BudgetExceeded(RuntimeError):
    pass


_KILL_SWITCH_OVERRIDE: str | None = None


@dataclass(frozen=True)
class BudgetGrant:
    session_id: str
    ip: str


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    return int(raw)


def _float_env(name: str) -> float | None:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return None
    return float(raw)


def set_kill_switch_override(state: str | None) -> None:
    global _KILL_SWITCH_OVERRIDE
    if state is None:
        _KILL_SWITCH_OVERRIDE = None
        return
    normalized = state.lower()
    if normalized not in {"on", "off"}:
        raise ValueError("kill switch state must be on or off")
    _KILL_SWITCH_OVERRIDE = normalized


def kill_switch_override() -> str | None:
    return _KILL_SWITCH_OVERRIDE


class LLMBudget:
    def __init__(self, conn: sqlite3.Connection | None = None) -> None:
        if conn is None:
            from arena.api.app import db

            conn = db()
        self.conn = conn
        storage.init(self.conn)
        self.ceiling_usd = _float_env("LLM_VIRAL_SPIKE_COST_CEILING_USD")
        self.max_calls_per_session = _int_env("LLM_MAX_CALLS_PER_SESSION", 8)
        self.max_calls_per_ip_window = _int_env("LLM_MAX_CALLS_PER_IP_WINDOW", 40)
        self.ip_window_seconds = _int_env("LLM_IP_WINDOW_SECONDS", 3600)
        self.max_concurrent_sessions = _int_env("LLM_MAX_CONCURRENT_SESSIONS", 4)

    def is_killed(self) -> bool:
        return _KILL_SWITCH_OVERRIDE == "on" or os.environ.get("LLM_GLOBAL_KILL_SWITCH", "off").lower() == "on"

    def acquire(self, session_id: str, ip: str) -> BudgetGrant:
        if self.is_killed():
            raise BudgetExceeded("LLM kill switch is on")
        if storage.count_session_calls(self.conn, session_id) >= self.max_calls_per_session:
            raise BudgetExceeded("LLM session call cap exceeded")
        if storage.count_ip_window_calls(self.conn, ip, self.ip_window_seconds) >= self.max_calls_per_ip_window:
            raise BudgetExceeded("LLM IP window call cap exceeded")
        if storage.count_concurrent_sessions(self.conn) >= self.max_concurrent_sessions:
            raise BudgetExceeded("LLM concurrent session cap exceeded")
        if self.ceiling_usd is not None and storage.total_cost_usd(self.conn) >= self.ceiling_usd:
            raise BudgetExceeded("LLM cost ceiling exceeded")
        storage.begin_concurrency(self.conn, session_id)
        return BudgetGrant(session_id=session_id, ip=ip)

    def release(
        self,
        grant: BudgetGrant,
        *,
        tokens_in: int = 0,
        tokens_out: int = 0,
        cost_usd_est: float = 0.0,
    ) -> None:
        try:
            storage.record_call(
                self.conn,
                session_id=grant.session_id,
                ip=grant.ip,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd_est=cost_usd_est,
            )
        finally:
            storage.end_concurrency(self.conn, grant.session_id)

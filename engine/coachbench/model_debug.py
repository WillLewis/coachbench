from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEBUG_ENV_VAR = "COACHBENCH_MODEL_DEBUG"
DEBUG_PATH_ENV_VAR = "COACHBENCH_MODEL_DEBUG_PATH"
DEFAULT_DEBUG_DIR = Path("data/eval/debug")


def _is_enabled() -> bool:
    return os.environ.get(DEBUG_ENV_VAR) == "1"


def _resolve_path(agent_name: str) -> Path:
    override = os.environ.get(DEBUG_PATH_ENV_VAR)
    if override:
        return Path(override)
    slug = agent_name.lower().replace(" ", "_")
    return DEFAULT_DEBUG_DIR / f"{slug}_raw.jsonl"


def log_model_decision(
    *,
    agent_name: str,
    side: str,
    turn_count: int,
    user_prompt: str,
    raw_text: str,
    parsed_json: dict[str, Any] | None,
    error: str | None,
    outcome: str,
    legal_set: list[str],
) -> None:
    """Append one JSONL entry per model decision when COACHBENCH_MODEL_DEBUG=1. No-op otherwise."""
    if not _is_enabled():
        return
    path = _resolve_path(agent_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent_name": agent_name,
        "side": side,
        "turn_count": int(turn_count),
        "user_prompt": user_prompt,
        "raw_text": raw_text,
        "parsed_json": parsed_json,
        "error": error,
        "outcome": outcome,
        "legal_set": list(legal_set),
    }
    line = json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")

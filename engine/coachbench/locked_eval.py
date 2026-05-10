from __future__ import annotations

import os
from typing import Any


class LockedEvalViolation(Exception):
    """Raised when an agent or environment violates locked-run constraints."""


LOCKED_LLM_ENV_VARS: frozenset[str] = frozenset({
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "OPENAI_ORG",
    "OPENAI_ORGANIZATION",
    "GOOGLE_API_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "COHERE_API_KEY",
    "HF_TOKEN",
    "HUGGING_FACE_HUB_TOKEN",
    "REPLICATE_API_TOKEN",
    "MISTRAL_API_KEY",
    "TOGETHER_API_KEY",
    "GROQ_API_KEY",
})


def is_locked_env() -> bool:
    """Return True iff COACHBENCH_LOCKED_EVAL=1 in os.environ."""
    return os.environ.get("COACHBENCH_LOCKED_EVAL") == "1"


def set_locked_env(locked: bool) -> None:
    """Set or clear COACHBENCH_LOCKED_EVAL. Idempotent."""
    if locked:
        os.environ["COACHBENCH_LOCKED_EVAL"] = "1"
        return
    os.environ.pop("COACHBENCH_LOCKED_EVAL", None)


def scrub_llm_env_vars() -> dict[str, str]:
    """Remove all LOCKED_LLM_ENV_VARS from os.environ. Return a dict of {var: prior_value} for restoration in tests."""
    snapshot: dict[str, str] = {}
    for key in LOCKED_LLM_ENV_VARS:
        prior = os.environ.pop(key, None)
        if prior is not None:
            snapshot[key] = prior
    return snapshot


def restore_llm_env_vars(snapshot: dict[str, str]) -> None:
    """Restore env vars from a snapshot returned by scrub_llm_env_vars. Used by tests."""
    for key, value in snapshot.items():
        os.environ[key] = value


def enforce_locked_or_raise(agent: Any, label: str) -> None:
    """If is_locked_env(), raise LockedEvalViolation when the agent or its class declares requires_network=True.
    The label argument is included in the error message for debugging.
    No-op when not locked."""
    if not is_locked_env():
        return
    requires_network = bool(
        getattr(agent, "requires_network", False)
        or getattr(agent.__class__, "requires_network", False)
    )
    if requires_network:
        raise LockedEvalViolation(f"{label} declares requires_network=True during locked eval")

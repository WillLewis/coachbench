from __future__ import annotations

from dataclasses import dataclass
import importlib
import json
import os
from pathlib import Path
from typing import Any

from .usage import LLMUsage


class LLMUnavailable(RuntimeError):
    pass


class LLMTimeout(RuntimeError):
    pass


class LLMHttpError(RuntimeError):
    pass


class LLMSchemaInvalid(ValueError):
    pass


DEFAULT_MODEL = "claude-opus-4-7"
PLACEHOLDER_COST_CEILING = "50"
DEFAULT_MAX_TOKENS = 700
DEFAULT_TIMEOUT_SECONDS = 15.0


@dataclass(frozen=True)
class ModelPricing:
    input_per_mtok: float
    output_per_mtok: float
    cache_write_5m_per_mtok: float
    cache_hit_per_mtok: float


MODEL_PRICING: dict[str, ModelPricing] = {
    "claude-opus-4-7": ModelPricing(5.0, 25.0, 6.25, 0.50),
    "claude-opus-4-6": ModelPricing(5.0, 25.0, 6.25, 0.50),
    "claude-opus-4-5": ModelPricing(5.0, 25.0, 6.25, 0.50),
    "claude-opus-4-1-20250805": ModelPricing(15.0, 75.0, 18.75, 1.50),
    "claude-sonnet-4-6": ModelPricing(3.0, 15.0, 3.75, 0.30),
    "claude-sonnet-4-5": ModelPricing(3.0, 15.0, 3.75, 0.30),
    "claude-haiku-4-5-20251001": ModelPricing(1.0, 5.0, 1.25, 0.10),
    "claude-haiku-4-5": ModelPricing(1.0, 5.0, 1.25, 0.10),
}


def configured_model() -> str:
    return os.environ.get("COACHBENCH_LLM_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def _require_cost_gate() -> None:
    raw = os.environ.get("LLM_VIRAL_SPIKE_COST_CEILING_USD", "").strip().removeprefix("$")
    if not raw or raw == PLACEHOLDER_COST_CEILING:
        raise LLMUnavailable("LLM cost ceiling is unset or still using the placeholder")
    try:
        if float(raw) <= 0:
            raise ValueError
    except ValueError as exc:
        raise LLMUnavailable("LLM cost ceiling must be a positive number") from exc


def _api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise LLMUnavailable("ANTHROPIC_API_KEY is unset")
    return key


def _pricing_for(model: str) -> ModelPricing:
    try:
        return MODEL_PRICING[model]
    except KeyError as exc:
        raise LLMUnavailable(f"unsupported CoachBench LLM model: {model}") from exc


def _system_prompt() -> str:
    return (Path(__file__).parent / "system_prompt.md").read_text(encoding="utf-8")


def _usage_value(usage: Any, field: str) -> int:
    if isinstance(usage, dict):
        return int(usage.get(field) or 0)
    return int(getattr(usage, field, 0) or 0)


def estimate_cost_usd(model: str, usage: Any) -> LLMUsage:
    pricing = _pricing_for(model)
    input_tokens = _usage_value(usage, "input_tokens")
    output_tokens = _usage_value(usage, "output_tokens")
    cache_creation_tokens = _usage_value(usage, "cache_creation_input_tokens")
    cache_read_tokens = _usage_value(usage, "cache_read_input_tokens")
    cost = (
        (input_tokens / 1_000_000) * pricing.input_per_mtok
        + (output_tokens / 1_000_000) * pricing.output_per_mtok
        + (cache_creation_tokens / 1_000_000) * pricing.cache_write_5m_per_mtok
        + (cache_read_tokens / 1_000_000) * pricing.cache_hit_per_mtok
    )
    return LLMUsage(
        tokens_in=input_tokens + cache_creation_tokens + cache_read_tokens,
        tokens_out=output_tokens,
        cost_usd_est=round(cost, 8),
    )


def _split_context(context: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    static_keys = {
        "task_schema",
        "canonical_prompt_examples",
        "parameter_glossary",
        "legal_parameters",
        "legal_concepts",
        "legal_graph_cards",
        "legal_identity_ids",
    }
    static = {key: context[key] for key in sorted(static_keys) if key in context}
    dynamic = {key: context[key] for key in sorted(context) if key not in static_keys}
    return static, dynamic


def _content_text(response: Any) -> str:
    content = getattr(response, "content", None)
    if not content:
        raise LLMSchemaInvalid("LLM response did not contain text content")
    first = content[0]
    if isinstance(first, dict):
        text = first.get("text")
    else:
        text = getattr(first, "text", None)
    if not isinstance(text, str) or not text.strip():
        raise LLMSchemaInvalid("LLM response text is empty")
    return text.strip()


def _parse_json_response(response: Any) -> dict[str, Any]:
    try:
        payload = json.loads(_content_text(response))
    except json.JSONDecodeError as exc:
        raise LLMSchemaInvalid("LLM response was not valid JSON") from exc
    if not isinstance(payload, dict):
        raise LLMSchemaInvalid("LLM response must be a JSON object")
    return payload


def call_llm_real(
    prompt: str,
    context: dict[str, Any],
    *,
    session_id: str,
    ip: str,
) -> tuple[dict[str, Any], LLMUsage]:
    del session_id, ip
    _require_cost_gate()
    model = configured_model()
    _pricing_for(model)
    try:
        anthropic = importlib.import_module("anthropic")
    except ModuleNotFoundError as exc:
        raise LLMUnavailable("anthropic SDK is not installed") from exc
    static_context, dynamic_context = _split_context(context)
    max_tokens = int(os.environ.get("COACHBENCH_LLM_MAX_TOKENS", str(DEFAULT_MAX_TOKENS)))
    timeout = float(os.environ.get("COACHBENCH_LLM_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS)))
    try:
        client = anthropic.Anthropic(api_key=_api_key(), timeout=timeout)
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=[
                {
                    "type": "text",
                    "text": _system_prompt(),
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "STATIC_CONTEXT\n" + json.dumps(static_context, sort_keys=True, separators=(",", ":")),
                            "cache_control": {"type": "ephemeral"},
                        },
                        {
                            "type": "text",
                            "text": "REQUEST\n" + json.dumps(
                                {"prompt": prompt, "context": dynamic_context},
                                sort_keys=True,
                                separators=(",", ":"),
                            ),
                        },
                    ],
                }
            ],
        )
    except TimeoutError as exc:
        raise LLMTimeout("Anthropic request timed out") from exc
    except Exception as exc:
        name = exc.__class__.__name__.lower()
        if "timeout" in name:
            raise LLMTimeout("Anthropic request timed out") from exc
        if (
            "api" in name
            or "http" in name
            or "connection" in name
            or "badrequest" in name
            or "rate" in name
            or hasattr(exc, "status_code")
        ):
            raise LLMHttpError(str(exc)) from exc
        raise
    return _parse_json_response(response), estimate_cost_usd(model, getattr(response, "usage", {}))

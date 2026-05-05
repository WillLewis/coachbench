from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from arena.api.deps import moderate
from coachbench.graph_loader import StrategyGraph

ALLOWED_CONSTRAINTS = {"max_turnover_risk", "require_legal_action", "prefer_concepts", "avoid_concepts"}


@dataclass(frozen=True)
class Tier1Config:
    agent_name: str
    side: str
    access_tier: str
    strategy_prompt: str | None
    constraints: dict
    rules: list[dict]


def _looks_like_python(text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in ("import ", "__", "eval(", "exec(", "open("))


def validate_tier1_config_dict(payload: dict[str, Any]) -> None:
    if payload.get("access_tier") != "prompt_policy":
        raise ValueError("tier1 config access_tier must be prompt_policy")
    if payload.get("side") not in {"offense", "defense"}:
        raise ValueError("side must be offense or defense")
    constraints = dict(payload.get("constraints", {}))
    unknown = {key for key in constraints if key not in ALLOWED_CONSTRAINTS and not key.startswith("max_") and not key.endswith("_rate")}
    if unknown:
        raise ValueError(f"unknown tier1 constraints: {sorted(unknown)}")
    if constraints.get("require_legal_action") is not True:
        raise ValueError("tier1 configs must set require_legal_action true")
    prompt = str(payload.get("strategy_prompt") or "")
    moderate(prompt)
    moderate(str(payload.get("agent_name", "")))
    if _looks_like_python(prompt) or _looks_like_python(json.dumps(payload.get("rules", []))):
        raise ValueError("tier1 configs must not contain Python-like execution patterns")
    graph = StrategyGraph()
    vocab = set(graph.offense_concepts() if payload.get("side") == "offense" else graph.defense_calls())
    referenced = set(constraints.get("prefer_concepts", [])) | set(constraints.get("avoid_concepts", []))
    referenced |= {rule.get("then") for rule in payload.get("rules", []) if isinstance(rule, dict)}
    unknown = {item for item in referenced if item and item not in vocab}
    if unknown:
        raise ValueError(f"unknown tier1 concepts: {sorted(unknown)}")


def load_tier1_config(path: Path) -> Tier1Config:
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_tier1_config_dict(payload)
    return Tier1Config(
        agent_name=payload["agent_name"],
        side=payload["side"],
        access_tier="prompt_policy",
        strategy_prompt=payload.get("strategy_prompt"),
        constraints=dict(payload.get("constraints", {})),
        rules=list(payload.get("rules", [])),
    )


class Tier1Adapter:
    access_tier = "prompt_policy"

    def __init__(self, config: Tier1Config) -> None:
        self.config = config
        self.name = config.agent_name

    def _predicate_matches(self, predicate: dict[str, Any], obs) -> bool:
        state = obs.game_state
        for key, expected in predicate.items():
            if key in {"down", "distance", "yardline", "points"}:
                if int(state.get(key) or 0) != int(expected):
                    return False
            elif key.startswith("belief."):
                belief_key = key.split(".", 1)[1]
                if float(obs.memory_summary.get("beliefs", {}).get(belief_key, 0.0)) <= float(expected):
                    return False
            elif key.startswith("count_recent("):
                concept = key.removeprefix("count_recent(").removesuffix(")")
                if obs.memory_summary.get("own_recent_calls", []).count(concept) < int(expected):
                    return False
            else:
                return False
        return True

    def _respects_constraints(self, concept: str, obs) -> bool:
        avoid = set(self.config.constraints.get("avoid_concepts", []))
        if concept in avoid and len(obs.legal_actions) > 1:
            return False
        recent = obs.memory_summary.get("own_recent_calls", [])
        for key, value in self.config.constraints.items():
            if key.startswith("max_") and key.endswith("_rate"):
                limited = key.removeprefix("max_").removesuffix("_rate")
                if concept == limited and recent and (recent.count(concept) / len(recent)) >= float(value):
                    return False
        return True

    def choose_action(self, obs) -> str:
        for rule in self.config.rules:
            concept = rule.get("then")
            if concept in obs.legal_actions and self._predicate_matches(dict(rule.get("if", {})), obs) and self._respects_constraints(concept, obs):
                return concept
        for concept in self.config.constraints.get("prefer_concepts", []):
            if concept in obs.legal_actions and self._respects_constraints(concept, obs):
                return concept
        candidates = [item for item in obs.legal_actions if self._respects_constraints(item, obs)]
        return sorted(candidates or obs.legal_actions)[0]

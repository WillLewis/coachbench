from __future__ import annotations

from pathlib import Path
from typing import Any

from coachbench.action_legality import ActionValidationError, LegalActionFacade
from coachbench.model_debug import log_model_decision
from coachbench.model_observation import render_observation_for_offense
from coachbench.providers import make_provider
from coachbench.schema import AgentMemory, OffenseAction


PROMPT_PATH = Path(__file__).parent / "prompts" / "model_offense_system.txt"


class ModelOffense:
    requires_network: bool = False
    name: str = "ModelOffense"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = dict(config or {})
        provider_name = str(self.config.get("provider", "anthropic"))
        provider_config = dict(self.config.get("provider_config", {}))
        self.provider = make_provider(provider_name, provider_config)
        self.requires_network = bool(self.provider.requires_network)
        self._system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
        self._internal_fallback_count = 0
        self.memory: dict[str, Any] = {"last_pick": None, "turn_count": 0}

    def observe(self, observation: dict[str, Any]) -> None:
        return None

    def choose_action(
        self,
        observation: dict[str, Any],
        memory: AgentMemory,
        legal: LegalActionFacade,
    ) -> OffenseAction:
        self.memory["turn_count"] = int(self.memory.get("turn_count", 0)) + 1
        user_prompt = render_observation_for_offense(observation)
        response = self.provider.query(system=self._system_prompt, user=user_prompt)
        legal_set = legal.legal_offense_concepts()

        def _log(outcome: str) -> None:
            log_model_decision(
                agent_name=self.name,
                side="offense",
                turn_count=int(self.memory["turn_count"]),
                user_prompt=user_prompt,
                raw_text=response.raw_text,
                parsed_json=response.parsed_json,
                error=response.error,
                outcome=outcome,
                legal_set=list(legal_set),
            )

        if response.parsed_json is None:
            self._internal_fallback_count += 1
            _log("fallback:no_valid_json")
            raise ActionValidationError([
                f"model_offense: provider returned no valid JSON (error={response.error!r}, raw={response.raw_text[:120]!r})"
            ])

        concept = response.parsed_json.get("concept_family")
        if not isinstance(concept, str) or not concept:
            self._internal_fallback_count += 1
            _log("fallback:missing_concept_family")
            raise ActionValidationError([
                f"model_offense: response missing or invalid concept_family: {response.parsed_json}"
            ])

        if concept not in legal_set:
            self._internal_fallback_count += 1
            _log(f"fallback:concept_not_legal:{concept}")
            raise ActionValidationError([
                f"model_offense: picked concept {concept!r} not in legal set: {legal_set}"
            ])

        self.memory["last_pick"] = concept
        _log(f"picked:{concept}")
        return legal.build_offense_action(concept, "balanced")

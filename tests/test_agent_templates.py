from __future__ import annotations

from agents.static_defense import StaticDefense
from agents.static_offense import StaticOffense
from agents.templates.defense_template import TemplateDefense
from agents.templates.offense_template import TemplateOffense
from coachbench.contracts import validate_replay_contract
from coachbench.engine import CoachBenchEngine


def test_offense_template_runs_against_static_defense() -> None:
    replay = CoachBenchEngine(seed=42).run_drive(TemplateOffense(), StaticDefense(), max_plays=2)

    validate_replay_contract(replay)
    assert replay["score"]["invalid_action_count"] == 0


def test_defense_template_runs_against_static_offense() -> None:
    replay = CoachBenchEngine(seed=42).run_drive(StaticOffense(), TemplateDefense(), max_plays=2)

    validate_replay_contract(replay)
    assert replay["score"]["invalid_action_count"] == 0

from __future__ import annotations

from agents.adaptive_offense import AdaptiveOffense
from agents.example_scouting_agent import ExampleScoutingOffense
from agents.static_defense import StaticDefense
from agents.static_offense import StaticOffense
from coachbench.engine import CoachBenchEngine
from coachbench.scouting import load_scouting_report


def test_existing_agents_skip_pre_drive_observation_cleanly() -> None:
    report = load_scouting_report("data/scouting_reports/pass_heavy_stale.json")
    replay = CoachBenchEngine(seed=42).run_drive(
        AdaptiveOffense(),
        StaticDefense(),
        offense_scouting=report,
        max_plays=1,
    )
    assert replay["score"]["invalid_action_count"] == 0


def test_scouting_agent_receives_report_once_before_first_play() -> None:
    agent = ExampleScoutingOffense()
    report = load_scouting_report("data/scouting_reports/pass_heavy_stale.json")
    CoachBenchEngine(seed=42).run_drive(agent, StaticDefense(), offense_scouting=report, max_plays=1)
    assert agent.report_count == 1
    assert agent.first_choose_saw_report is True


def test_pre_drive_observation_contains_only_declared_keys() -> None:
    agent = ExampleScoutingOffense()
    report = load_scouting_report("data/scouting_reports/pass_heavy_stale.json")
    CoachBenchEngine(seed=42).run_drive(agent, StaticDefense(), offense_scouting=report, max_plays=1)
    assert set(agent._report or {}) == {"report_id", "freshness", "completeness", "estimated_traits", "confidence", "notes"}


def test_no_scouting_kwargs_make_no_pre_drive_calls() -> None:
    agent = ExampleScoutingOffense()
    CoachBenchEngine(seed=42).run_drive(agent, StaticDefense(), max_plays=1)
    assert agent.report_count == 0

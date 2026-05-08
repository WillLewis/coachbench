from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import _path  # noqa: F401
from agents.adaptive_defense import AdaptiveDefense
from agents.adaptive_offense import AdaptiveOffense
from agents.static_defense import StaticDefense
from agents.static_offense import StaticOffense
from coachbench.contracts import validate_replay_contract
from coachbench.engine import CoachBenchEngine
from coachbench.matchup_traits import load_matchup_traits
from coachbench.roster_budget import load_roster
from coachbench.scouting import load_scouting_report


def load_agent_garage_profiles():
    return json.loads(Path("agent_garage/profiles.json").read_text(encoding="utf-8"))


def profile_config(profiles, side: str, key: str):
    group = "offense_archetypes" if side == "offense" else "defense_archetypes"
    profile = dict(profiles[group][key])
    profile["profile_key"] = key
    return profile


def build_agents(offense: str, defense: str):
    profiles = load_agent_garage_profiles()
    garage_config = {"source": "agent_garage_profiles_v1"}

    if offense == "adaptive":
        offense_profile = profile_config(profiles, "offense", "aggressive_shot_taker")
        offense_agent = AdaptiveOffense(offense_profile)
        garage_config["offense_profile"] = offense_profile
    else:
        offense_agent = StaticOffense()
        garage_config["offense_profile"] = {"profile_key": "static_baseline", "label": "Static Baseline"}

    if defense == "adaptive":
        defense_profile = profile_config(profiles, "defense", "coverage_shell_conservative")
        defense_agent = AdaptiveDefense(defense_profile)
        garage_config["defense_profile"] = defense_profile
    else:
        defense_agent = StaticDefense()
        garage_config["defense_profile"] = {"profile_key": "static_baseline", "label": "Static Baseline"}

    return offense_agent, defense_agent, garage_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a CoachBench showcase replay.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--offense", choices=["static", "adaptive"], default="adaptive")
    parser.add_argument("--defense", choices=["static", "adaptive"], default="adaptive")
    parser.add_argument("--out", default="data/demo_replay.json")
    parser.add_argument("--copy-ui", action="store_true")
    parser.add_argument("--offense-roster", type=Path)
    parser.add_argument("--defense-roster", type=Path)
    parser.add_argument("--matchup-traits", type=Path)
    parser.add_argument("--offense-scouting", type=Path)
    parser.add_argument("--defense-scouting", type=Path)
    args = parser.parse_args()

    engine = CoachBenchEngine(seed=args.seed)
    offense_agent, defense_agent, garage_config = build_agents(args.offense, args.defense)
    replay = engine.run_drive(
        offense_agent,
        defense_agent,
        agent_garage_config=garage_config,
        offense_roster=load_roster(args.offense_roster) if args.offense_roster else None,
        defense_roster=load_roster(args.defense_roster) if args.defense_roster else None,
        matchup_traits=load_matchup_traits(args.matchup_traits) if args.matchup_traits else None,
        offense_scouting=load_scouting_report(args.offense_scouting) if args.offense_scouting else None,
        defense_scouting=load_scouting_report(args.defense_scouting) if args.defense_scouting else None,
    )
    validate_replay_contract(replay)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(replay, indent=2) + "\n", encoding="utf-8")

    if args.copy_ui:
        ui_out = Path("ui") / "demo_replay.json"
        ui_out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out, ui_out)

    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

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


def load_agent_garage_profiles():
    return json.loads(Path("agent_garage/profiles.json").read_text(encoding="utf-8"))


def profile_config(profiles, side: str, key: str):
    group = "offense_archetypes" if side == "offense" else "defense_archetypes"
    profile = dict(profiles[group][key])
    profile["profile_key"] = key
    return profile


def build_agents(offense: str, defense: str):
    profiles = load_agent_garage_profiles()
    garage_config = {"source": "agent_garage_profiles_v0"}

    if offense == "adaptive":
        offense_profile = profile_config(profiles, "offense", "misdirection_artist")
        offense_agent = AdaptiveOffense(offense_profile)
        garage_config["offense_profile"] = offense_profile
    else:
        offense_agent = StaticOffense()
        garage_config["offense_profile"] = {"profile_key": "static_baseline", "label": "Static Baseline"}

    if defense == "adaptive":
        defense_profile = profile_config(profiles, "defense", "disguise_specialist")
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
    args = parser.parse_args()

    engine = CoachBenchEngine(seed=args.seed)
    offense_agent, defense_agent, garage_config = build_agents(args.offense, args.defense)
    replay = engine.run_drive(
        offense_agent,
        defense_agent,
        agent_garage_config=garage_config,
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

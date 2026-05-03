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
from coachbench.engine import CoachBenchEngine


def build_agents(offense: str, defense: str):
    offense_agent = AdaptiveOffense() if offense == "adaptive" else StaticOffense()
    defense_agent = AdaptiveDefense() if defense == "adaptive" else StaticDefense()
    return offense_agent, defense_agent


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a CoachBench showcase replay.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--offense", choices=["static", "adaptive"], default="adaptive")
    parser.add_argument("--defense", choices=["static", "adaptive"], default="adaptive")
    parser.add_argument("--out", default="data/demo_replay.json")
    parser.add_argument("--copy-ui", action="store_true")
    args = parser.parse_args()

    engine = CoachBenchEngine(seed=args.seed)
    offense_agent, defense_agent = build_agents(args.offense, args.defense)
    replay = engine.run_drive(
        offense_agent,
        defense_agent,
        agent_garage_config={
            "offense_archetype": "Misdirection Artist" if args.offense == "adaptive" else "Efficiency Optimizer",
            "defense_archetype": "Disguise Specialist" if args.defense == "adaptive" else "Coverage Shell Conservative",
            "source": "starter_default",
        },
    )

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

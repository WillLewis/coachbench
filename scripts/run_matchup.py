from __future__ import annotations

import argparse
from pathlib import Path

try:
    from _evaluation import load_teams, run_direction, write_json
except ModuleNotFoundError:
    from scripts._evaluation import load_teams, run_direction, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one Team A offense vs Team B defense matchup.")
    parser.add_argument("--team-a", required=True, type=Path)
    parser.add_argument("--team-b", required=True, type=Path)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-plays", type=int, default=8)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    team_a, team_b = load_teams(args.team_a, args.team_b)
    replay = run_direction(
        offense_team=team_a,
        defense_team=team_b,
        seed=args.seed,
        max_plays=args.max_plays,
        matchup_direction=f"{team_a.team_id}_oc_vs_{team_b.team_id}_dc",
    )
    replay["agent_garage_config"]["team_a_id"] = team_a.team_id
    replay["agent_garage_config"]["team_b_id"] = team_b.team_id
    write_json(args.out, replay)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()

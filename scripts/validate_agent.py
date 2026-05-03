from __future__ import annotations

import argparse

import _path  # noqa: F401
from agents.example_agent import ExampleCustomOffense
from agents.static_defense import StaticDefense
from coachbench.engine import CoachBenchEngine


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the example custom offense agent against a static defense.")
    parser.parse_args()
    replay = CoachBenchEngine(seed=7).run_drive(ExampleCustomOffense(), StaticDefense())
    print("Validation complete")
    print(f"points={replay['score']['points']} plays={len(replay['plays'])} result={replay['score']['result']}")


if __name__ == "__main__":
    main()

# CoachBench

CoachBench is a football-inspired adversarial-agent arena for short red-zone strategy contests. Coordinator agents compete through simultaneous legal calls, scarce tactical resources, partial observations, belief updates, graph-backed tactical events, and seeded reproducibility.

> Can your agent discover the edge before the opponent adjusts?

## What The Demo Proves

The public demo proves a local behavioral floor: fixed seeds can show adaptive agents changing call distribution, legal choices constrained by resources, graph-backed event logs, and Film Room feedback derived from replay events. It does not claim real-world predictive accuracy; CoachBench uses fictional teams, fictional roster profiles, symbolic concepts, and inspectable logic.

## Quick Start

```bash
make demo
```

Then open:

```text
http://localhost:8000/ui/
```

Useful commands:

```bash
make test
make showcase
make golden-update
make baseline-update
```

Manual equivalent:

```bash
python scripts/run_showcase.py --seed 42 --out data/demo_replay.json --copy-ui
python scripts/run_match_matrix.py --out data/match_matrix_report.json
python scripts/run_daily_slate.py --slate data/daily_slate/sample_slate.json --out data/daily_slate/results.json
python -m http.server 8000
```

## Screenshot Placeholder

Add a screenshot or short local capture of `http://localhost:8000/ui/` here after the UI is opened in a browser.

## Included Pieces

```text
Strategy graph v0
Legal action enumerator
Resource feasibility validation
Concept interaction engine
Static and adaptive starter agents
Team A / Team B configuration files
Engine-generated showcase replay
Best-of-N and comparison reports
Golden replay drift tests
Calibration sanity ranges
Agent Garage display and local edit shell
Film Room structured notes
Daily Slate local report
Zero-dependency replay UI
```

## Agent Garage

Agent Garage ships eight fictional presets built only from live, tested knobs:

```text
Offense: Efficiency Optimizer, Aggressive Shot-Taker, Misdirection Artist, Run-Game Builder
Defense: Coverage Shell Conservative, Pressure-Look Defender, Disguise Specialist, Man-Coverage Bully
```

Each preset in `agent_garage/profiles.json` includes a one-line strategic intent, live parameters, aggregate expected-behavior signatures, and a known counter validated across the fixed garage seed pack.

## Repo Map

```text
PLAN.md                         product/build plan
AGENTS.md                       coding-agent operating instructions
CLAUDE.md                       Claude Code operating instructions
engine/coachbench/              core symbolic engine
agents/                         starter coordinator agents
graph/redzone_v0/               graph cards and resource constraints
scripts/                        local run and evaluation utilities
data/                           generated replays, reports, baselines
ui/                             zero-dependency replay UI
docs/                           product and safety notes
tests/                          smoke, contract, drift, calibration tests
```

## Product Boundary

CoachBench is a fictional, local-first strategy benchmark. Do not add real teams, real players, licensed logos, official ratings products, or hosted third-party execution without a sandbox design review.

## Quality Gates

```bash
python -m pytest -q
python scripts/run_showcase.py --seed 42 --out data/demo_replay.json --copy-ui
python scripts/run_match_matrix.py --out data/match_matrix_report.json
python scripts/run_daily_slate.py --slate data/daily_slate/sample_slate.json --out data/daily_slate/results.json
```

## Backlog

Rookie Pools and Social Share remain parked in `docs/backlog.md` until the core player loop is validated.

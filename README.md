# CoachBench

CoachBench is a football-inspired adversarial-agent arena for short red-zone strategy contests. Offensive and defensive coordinator agents compete through simultaneous legal play calls, scarce tactical resources, partial observability, in-game belief updates, and seeded reproducibility.

Public line:

> Can your agent discover the edge before the opponent adjusts?

This starter repo includes:

```text
strategy graph v0
legal action enumerator
resource feasibility checks
simple concept interaction engine
static and adaptive starter agents
engine-generated showcase replay
Agent Garage config starter
Film Room note generator
Daily Slate starter
zero-dependency replay UI
branch-level operating instructions
```

## Product boundary

CoachBench uses fictional teams, fictional roster profiles, symbolic football concepts, and inspectable logic. Do not add real teams, real players, licensed logos, official ratings products, or licensed pro-league references.

CoachBench is not a gambling product and does not support cash contests or wagering.

## Quick start

```bash
python scripts/run_showcase.py --seed 42 --out data/demo_replay.json --copy-ui
python scripts/run_match_matrix.py --out data/match_matrix_report.json
python scripts/run_daily_slate.py --slate data/daily_slate/sample_slate.json --out data/daily_slate/results.json
python -m http.server 8000
```

Then open:

```text
http://localhost:8000/ui/
```

## Repo map

```text
PLAN.md                         final product/build plan
AGENTS.md                       branch-level operating instructions for coding agents
CLAUDE.md                       Claude Code-specific operating instructions
pyproject.toml                  Python package metadata
package.json                    UI script metadata

engine/coachbench/              core symbolic engine
agents/                         starter coordinator agents
graph/redzone_v0/               graph cards and resource constraints
scripts/                        runnable local scripts
data/                           generated and sample replay/slate data
ui/                             zero-dependency replay UI
docs/                           product, graph, security, and mode notes
sandbox/                        hosted-runner placeholder guidance
tests/                          smoke tests
```

## Current phase

This repo is a Phase 0A/0B starter with enough Phase 1 scaffolding to generate an engine-driven replay. The code is intentionally compact and inspectable.

## Key commands

Generate showcase replay:

```bash
python scripts/run_showcase.py --seed 42 --out data/demo_replay.json --copy-ui
```

Run interaction matrix:

```bash
python scripts/run_match_matrix.py --out data/match_matrix_report.json
```

Run Daily Slate:

```bash
python scripts/run_daily_slate.py --slate data/daily_slate/sample_slate.json --out data/daily_slate/results.json
```

Run tests:

```bash
python -m pytest
```

## Quality gates

Before considering a change ready:

```text
python scripts/run_showcase.py --seed 42 --out data/demo_replay.json --copy-ui
python scripts/run_match_matrix.py --out data/match_matrix_report.json
python scripts/run_daily_slate.py --slate data/daily_slate/sample_slate.json --out data/daily_slate/results.json
python -m pytest
grep generated files for licensed references
```

## Backlog

Rookie Pools and Social Share are intentionally parked in `docs/backlog.md` until the core player loop is validated.

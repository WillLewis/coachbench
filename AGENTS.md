# AGENTS.md

## Mission

Build CoachBench as a football-inspired adversarial-agent arena where coordinator agents compete in short red-zone strategy contests under simultaneous legal actions, resource constraints, partial observability, belief updates, and seeded reproducibility.

The current branch goal is to preserve a clean starter implementation for:

```text
Phase 0A: Spec Lock
Phase 0B: Static Schema/UI Proof
Phase 1 scaffold: engine-generated showcase replay
```

## Non-negotiable product constraints

1. Do not add real teams, real players, licensed logos, official ratings products, or licensed pro-league references.
2. Do not add cash contests, wagering, odds, betting flows, or payout language.
3. Do not let language-model text create tactical truth. Tactical truth comes from graph data and engine code.
4. Do not resolve illegal actions as gameplay. Prevent them through legal action generation and validation.
5. Do not leak hidden/debug fields into agent observations.
6. Do not implement hosted third-party execution without sandbox design review.
7. Keep Rookie Pools and Social Share in Backlog until explicitly promoted.

## Active product additions

Agent Garage, Film Room, and Daily Slate are active plan items.

### Agent Garage

Agent Garage exposes visible config parameters and coach-style accessibility labels. It must compile into legal agent policies. No archetype may bypass the legal action enumerator, resource constraints, or observation contract.

### Film Room

Film Room summarizes structured engine events. It may explain turning points, belief changes, resource mistakes, and suggested tweaks. It must not invent hidden facts or unsupported tactics.

### Daily Slate

Daily Slate runs fixed fictional challenge seeds and emits reproducible reports. It must remain non-wagering and strategy-focused.

## Backlog discipline

Backlog items are not implementation targets unless the plan changes.

Current Backlog:

```text
Rookie Pools
Social Share Features
```

## Architecture rules

Preferred flow:

```text
Strategy Graph
  -> Legal Action Enumerator
  -> Resource Feasibility Validator
  -> Concept Interaction Engine
  -> Resolution Engine
  -> Observation + Belief Update
  -> Replay JSON
  -> UI / Film Room / Daily Slate
```

Keep modules small, deterministic, and inspectable.

## Required starter commands

After changes, run:

```bash
python scripts/run_showcase.py --seed 42 --out data/demo_replay.json --copy-ui
python scripts/run_match_matrix.py --out data/match_matrix_report.json
python scripts/run_daily_slate.py --slate data/daily_slate/sample_slate.json --out data/daily_slate/results.json
python -m pytest
```

## File responsibilities

```text
PLAN.md                         product/build plan
graph/redzone_v0/*.json         graph, interactions, constraints, validation examples
engine/coachbench/*.py          core engine and schemas
agents/*.py                     starter coordinator agents
scripts/*.py                    local run/eval utilities
data/*.json                     generated/sample replay and slate artifacts
ui/*                            zero-dependency replay UI
docs/*                          product explanations and safety notes
```

## Style rules

- Prefer explicit data structures over magic strings.
- Keep seeded behavior deterministic.
- Keep action vocabularies compact until the benchmark stabilizes.
- Use fictional names and neutral terminology.
- Document limitations instead of overclaiming realism.
- Make failures explicit and easy to debug.

## Acceptance checklist

A change is not ready unless:

```text
legal action validation still rejects impossible calls
same seed produces same replay
agent observations exclude hidden/debug fields
replay JSON can load in UI
Film Room notes are derived from replay events
Daily Slate report is reproducible
no banned licensed references are introduced
```

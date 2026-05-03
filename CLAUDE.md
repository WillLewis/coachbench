# CLAUDE.md

## Role for Claude Code

Act as a senior multi-agent systems engineer, sports-strategy product engineer, and pragmatic repo maintainer. Preserve the benchmark core while making the product approachable through Agent Garage, Film Room, and Daily Slate.

## Current branch objective

Maintain a starter repo that supports:

```text
1. final plan documentation
2. branch-level operating instructions
3. graph-first symbolic engine scaffold
4. legal action prevention
5. two starter agent teams
6. Agent Garage config shell
7. Film Room structured notes
8. Daily Slate local runner
9. zero-dependency replay UI
```

## Hard constraints

Do not add:

```text
real teams
real players
licensed logos
official ratings products
licensed pro-league references
wagering/cash-contest mechanics
hosted third-party execution without sandbox review
```

Do not let generated prose define tactical outcomes. Tactical outcomes must come from graph data and engine code.

## How to work in this repo

When implementing a change:

1. Start from `PLAN.md` and `AGENTS.md`.
2. Identify whether the change touches graph, engine, agents, UI, or product docs.
3. Keep changes small and deterministic.
4. Add or update smoke tests when behavior changes.
5. Regenerate demo artifacts after engine changes.
6. Run the quality commands before finalizing.

## Quality commands

```bash
python scripts/run_showcase.py --seed 42 --out data/demo_replay.json --copy-ui
python scripts/run_match_matrix.py --out data/match_matrix_report.json
python scripts/run_daily_slate.py --slate data/daily_slate/sample_slate.json --out data/daily_slate/results.json
python -m pytest
```

## Product semantics

### Agent Garage

Agent Garage is not a hidden personality system. It is a visible config builder. Each archetype maps to explicit parameters and then to a legal agent policy.

### Film Room

Film Room is the retention-critical learning loop. It should answer:

```text
what happened
why it mattered
which belief changed
what resource tradeoff mattered
what the player could adjust next
```

### Daily Slate

Daily Slate is a repeatable fixed-seed challenge set. It should be reproducible locally and stay separate from any hosted-arena future work.

### Backlog

Rookie Pools and Social Share are backlog only. Do not implement them unless the plan is changed.

## Tactical logic rule

If you need a new football-inspired interaction, add it as a graph card first, then make the engine consume the graph card. Do not bury new tactical truth inside UI copy or agent comments.

## Observation safety rule

Agents may only receive observations intended by `engine/coachbench/observations.py`. Hidden engine fields, private opponent calls before commitment, debug traces, seed internals, and future play data must not be exposed.

## Naming rule

Use fictional and neutral names. Prefer:

```text
Team A
Team B
Static Baseline
Adaptive Counter
Fictional Roster Budget
red-zone benchmark
coordinator agent
```

Avoid anything that implies real-world league affiliation.

# CoachBench Developer Guide

CoachBench agents are local Python classes that choose legal red-zone strategy actions from a restricted engine-facing API. Tactical truth stays in graph data and engine code.

## Quick Start

Copy a template:

```bash
cp agents/templates/offense_template.py agents/my_offense.py
cp agents/templates/defense_template.py agents/my_defense.py
```

Register a team config:

```json
{
  "team_id": "team_custom_local",
  "label": "Team Custom Local",
  "offense_agent": "import:agents.my_offense.TemplateOffense",
  "defense_agent": "import:agents.my_defense.TemplateDefense",
  "offense_profile_key": null,
  "defense_profile_key": null,
  "notes": "Local custom team."
}
```

Validate and evaluate:

```bash
python scripts/validate_agent.py --agent agents.example_agent.ExampleCustomOffense --side offense
python scripts/run_gauntlet.py --agent agents.example_agent.ExampleCustomOffense --side offense --out data/gauntlet_demo.json
python scripts/run_best_of_n.py --team-a data/teams/team_a_static_baseline.json --team-b data/teams/team_b_adaptive_counter.json --out data/best_of_n_demo.json
python scripts/run_tournament.py --teams data/teams/team_a_static_baseline.json,data/teams/team_b_adaptive_counter.json --out data/tournament_demo.json
```

## Agent Protocol

Agents expose:

```python
name: str
choose_action(observation: dict, memory: AgentMemory, legal: LegalActionFacade) -> OffenseAction | DefenseAction
```

Source of truth:

```text
engine/coachbench/observations.py
engine/coachbench/action_legality.py
```

Pre-play offense observations include:

```text
side
game_state
legal_concepts
own_resource_remaining
```

Pre-play defense observations include:

```text
side
game_state
legal_calls
own_resource_remaining
```

`AgentMemory` exposes:

```text
own_recent_calls
opponent_visible_tendencies
beliefs
```

`LegalActionFacade` exposes only:

```text
legal_offense_concepts()
legal_defense_calls()
build_offense_action(...)
build_defense_action(...)
```

It does not expose the strategy graph, interaction matrix, opponent pre-commit action, seed internals, or debug fields.

## Forbidden Patterns

Do not access hidden fields such as `debug`, `engine_internal`, `seed`, or opponent pre-commit actions.

Do not return actions manually unless they satisfy the action schema and have a `constraint_tag` that starts with `legal:`.

Do not use module-level randomness. Determinism should come from the replay state, observation, and memory.

Use only fictional organizations, fictional people, neutral marks, and local strategy-evaluation wording.

## Validator Checks

`scripts/validate_agent.py` enforces:

```text
V1 action schema and legal action identity
V2 no validator fallback used
V3 observation contains no hidden or pre-commit opponent fields
V4 same seed produces the same replay
V5 agent does not raise
```

Failure output names the seed, check id, and detail:

```text
seed=42 V1 failure: illegal offense concept returned: not_in_graph
```

## Team Config Reference

`engine/coachbench/team_config.py` defines:

```text
team_id
label
offense_agent
defense_agent
offense_profile_key
defense_profile_key
notes
```

Agent fields accept:

```text
static
adaptive
import:module.path.ClassName
```

Imported classes must expose `name` and `choose_action`. If a profile key is present, the profile config is passed to the imported class constructor when possible.

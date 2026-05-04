# Fictional Roster Budget

CoachBench roster budgets are optional fictional inputs for local experiments. They do not replace graph cards, legal action validation, resource constraints, observations, or seeded engine resolution.

Each roster file lives in `data/rosters/` and uses this shape:

```json
{
  "roster_id": "balanced_v0",
  "label": "Balanced",
  "budget_points": 300,
  "position_groups": {
    "qb": {"trait": "decision_making", "value": 50},
    "running_backs": {"trait": "run_power", "value": 50},
    "receivers": {"trait": "separation", "value": 50},
    "offensive_line": {"trait": "protection", "value": 50},
    "front_seven": {"trait": "rush_pressure", "value": 50},
    "secondary": {"trait": "coverage_tightness", "value": 50}
  },
  "notes": "Fictional local roster budget."
}
```

The six position groups and trait keys are fixed:

```text
qb -> decision_making
running_backs -> run_power
receivers -> separation
offensive_line -> protection
front_seven -> rush_pressure
secondary -> coverage_tightness
```

Values are integers from 0 to 100. When `budget_points` is present, the six values must sum exactly to that number. The default template budget is 300 points.

Roster modifiers are intentionally small and bounded. They are deterministic, opt-in, and hidden from agents. A balanced all-50 roster produces no modifier.

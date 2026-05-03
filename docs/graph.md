# Strategy Graph

The graph is the source of football-inspired tactical truth.

## Files

```text
graph.meta.json
concepts.json
interactions.json
belief_model.json
resolution_model.json
resource_constraints.json
graph_tests.json
```

## Invariants

```text
every strong tactic has a counter
every interaction has documented limitations
modifiers remain within safe bounds
resource-heavy calls spend constrained resources
drive-level resource budgets reduce legal action sets over a drive
action fields are declared on concept cards
belief and resolution tuning live in graph model files
no real teams, players, logos, or official ratings
```

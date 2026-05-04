# Film Room

Film Room explains why a match unfolded the way it did and gives the player a next adjustment.

## Required output

```text
headline
turning point
structured notes
suggested tweaks
graph-card references
```

## Source of truth

Film Room must derive from replay events and graph cards. It should not invent tactics, hidden truth, or real-world references.

## Starter definitions

Headlines use the final play's `terminal_reason` first, then points. Turnovers, turnover on downs, and out-of-plays stops should read differently even when each scores zero points.

The turning point is the play with the largest absolute `expected_value_delta`. That value is calculated before random yardage noise and before the realized success/failure roll, so the label means "largest graph/model swing," not necessarily the largest realized yardage swing.

Structured notes are generated from observed tactical events and the matched interaction card's `name`, `id`, and `limitations`. Agent intent language is reserved for a future structured agent rationale field; P0 Film Room should not infer why an agent chose a call.

Daily Slate robustness guidance belongs in the slate report summary, not in generic per-replay Film Room notes.

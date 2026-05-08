# Garage Audit Decisions

## Wire-up in 2.5.2

- `risk_tolerance`: wire. Expected signal: `drive_outcome`, through legal action `risk_level` choices already validated by `engine/coachbench/action_legality.py:106,135` and resolved by `graph/redzone_v0/resolution_model.json:4`. New graph work required: no.
- `explosive_shot_tolerance`: wire. Expected signal: `play_distribution`, with secondary `graph_event_frequency` for `redzone.vertical_vs_two_high.v1`. New graph work required: no; `vertical_shot` exists in `graph/redzone_v0/concepts.json:95` and the capped-window card exists at `graph/redzone_v0/interactions.json:192`.
- `run_pass_tendency`: wire. Expected signal: `play_distribution`, especially first-down run/pass mix and sequence-triggered `play_action_flood`. New graph work required: no; run concepts, pass concepts, and `redzone.play_action_after_run_tendency.v1` already exist at `graph/redzone_v0/concepts.json:4,17,30,43,82` and `graph/redzone_v0/interactions.json:146`.

## Delete in 2.5.2

- `pressure_punish_threshold`: delete. UI control should be removed, not hidden, because it is in PLAN/UI (`PLAN.md:492`, `ui/app.js:15,18,936`) but has no `profiles.json` field and no agent config consumption. Existing pressure decisions are already represented by `screen_trigger_confidence` and `pressure_frequency`.
- `resource_conservation`: delete. UI control should be removed from editable Garage, not hidden; old replay JSON can still be displayed read-only if encountered. It is in PLAN/UI (`PLAN.md:498`, `ui/app.js:16,920,942`) but has no `profiles.json` field and no agent config consumption.

## No Decision Needed

- `label` remains live display metadata, not a tweak target.
- `adaptation_speed`, `screen_trigger_confidence`, `disguise_sensitivity`, `pressure_frequency`, and `counter_repeat_tolerance` already change current adaptive agent behavior.

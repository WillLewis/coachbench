# Garage Parameter Audit

Scope note: `label` is included because it is a repeated profile field, but it is display metadata rather than a tunable behavior parameter. `pressure_punish_threshold` and `resource_conservation` are included because PLAN/UI expose them as Garage controls even though they are absent from `profiles.json` and agent config consumption.

| parameter | profile_path | consumed_in (file:line, "none" if dead) | agent_behavior_changed | observable_signal | film_room_can_cite | classification |
|---|---|---|---|---|---|---|
| `label` | `agent_garage/profiles.json:4,12,20,28,38,45,52,59` | none in agents; display metadata read at `ui/app.js:926` | no | none | no | live |
| `risk_tolerance` | `agent_garage/profiles.json:5,13,21,29,39,46,53,60` | none | no | none | no | wire-up |
| `adaptation_speed` | `agent_garage/profiles.json:6,14,22,30` | `agents/adaptive_offense.py:14`; behavior gates at `agents/adaptive_offense.py:23,29,33` | yes | play_distribution | yes | live |
| `pressure_punish_threshold` | none; PLAN/UI-only at `PLAN.md:492`, `ui/app.js:15,18,936` | none | no | none | no | delete |
| `screen_trigger_confidence` | `agent_garage/profiles.json:7,15,23,31` | `agents/adaptive_offense.py:15`; behavior gates at `agents/adaptive_offense.py:24,25,31`; example use at `agents/example_agent.py:16,31` | yes | graph_event_frequency | yes | live |
| `explosive_shot_tolerance` | `agent_garage/profiles.json:8,16,24,32` | stored by adaptive offense at `agents/adaptive_offense.py:16`; example behavior at `agents/example_agent.py:17,39` | partial: yes in example agent, no in `AdaptiveOffense` | play_distribution | needs-work | wire-up |
| `run_pass_tendency` | `agent_garage/profiles.json:9,17,25,33` | none | no | none | no | wire-up |
| `disguise_sensitivity` | `agent_garage/profiles.json:40,47,54,61` | `agents/adaptive_defense.py:14`; behavior gate at `agents/adaptive_defense.py:32,33`; example use at `agents/example_agent.py:53,72,73` | yes | play_distribution | yes | live |
| `pressure_frequency` | `agent_garage/profiles.json:41,48,55,62` | `agents/adaptive_defense.py:15`; behavior gate at `agents/adaptive_defense.py:34,37` | yes | resource_burn | yes | live |
| `counter_repeat_tolerance` | `agent_garage/profiles.json:42,49,56,63` | `agents/adaptive_defense.py:16`; behavior gate at `agents/adaptive_defense.py:22,28,29`; example use at `agents/example_agent.py:54,70,71` | yes | play_distribution | yes | live |
| `resource_conservation` | none; PLAN/UI-only at `PLAN.md:498`, `ui/app.js:16,920,942` | none | no | none | no | delete |

# Film Room Tweak Metadata Schema

This schema restricts tweak targets to fields already present in `agent_garage/profiles.json`, excluding display-only `label`. Current engine events do not emit stable replay event IDs, so examples use `source.graph_card_id`; `source.replay_event_id` is reserved for a later replay event identifier.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://coachbench.local/schemas/film-room-tweak-v0.json",
  "title": "CoachBench Film Room Structured Tweak",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "tweak_id",
    "parameter",
    "direction",
    "magnitude",
    "evidence",
    "source",
    "rationale"
  ],
  "properties": {
    "tweak_id": {
      "type": "string",
      "pattern": "^twk_[a-z0-9_]+$"
    },
    "parameter": {
      "type": "string",
      "enum": [
        "risk_tolerance",
        "adaptation_speed",
        "screen_trigger_confidence",
        "explosive_shot_tolerance",
        "run_pass_tendency",
        "disguise_sensitivity",
        "pressure_frequency",
        "counter_repeat_tolerance"
      ]
    },
    "direction": {
      "type": "string",
      "enum": ["increase", "decrease", "set"]
    },
    "magnitude": {
      "oneOf": [
        {
          "type": "string",
          "enum": ["small", "medium", "large"]
        },
        {
          "type": "number"
        }
      ]
    },
    "target_value": {
      "oneOf": [
        { "type": "number" },
        { "type": "string" },
        { "type": "boolean" }
      ]
    },
    "evidence": {
      "type": "object",
      "additionalProperties": false,
      "required": ["signal", "observed_value", "threshold", "play_indices"],
      "properties": {
        "signal": {
          "type": "string",
          "enum": [
            "play_distribution",
            "belief_trajectory",
            "resource_burn",
            "graph_event_frequency",
            "drive_outcome"
          ]
        },
        "observed_value": {
          "oneOf": [
            { "type": "number" },
            { "type": "string" },
            { "type": "boolean" },
            { "type": "object" }
          ]
        },
        "threshold": {
          "oneOf": [
            { "type": "number" },
            { "type": "string" },
            { "type": "boolean" },
            { "type": "object" }
          ]
        },
        "play_indices": {
          "type": "array",
          "items": {
            "type": "integer",
            "minimum": 1
          },
          "minItems": 1,
          "uniqueItems": true
        }
      }
    },
    "source": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "graph_card_id": {
          "type": "string",
          "pattern": "^redzone\\."
        },
        "replay_event_id": {
          "type": "string",
          "minLength": 1
        }
      },
      "anyOf": [
        { "required": ["graph_card_id"] },
        { "required": ["replay_event_id"] }
      ]
    },
    "rationale": {
      "type": "object",
      "additionalProperties": false,
      "required": ["template_id", "arguments", "rendered"],
      "properties": {
        "template_id": {
          "type": "string",
          "enum": [
            "belief_event_crossed_threshold",
            "event_count_crossed_threshold",
            "resource_burn_crossed_threshold",
            "play_mix_crossed_threshold",
            "drive_outcome_after_event"
          ]
        },
        "arguments": {
          "type": "object",
          "additionalProperties": false,
          "required": [
            "play_indices",
            "signal",
            "event_tag",
            "graph_card_id",
            "observed_value",
            "threshold",
            "parameter",
            "direction"
          ],
          "properties": {
            "play_indices": {
              "type": "array",
              "items": { "type": "integer", "minimum": 1 },
              "minItems": 1,
              "uniqueItems": true
            },
            "signal": {
              "type": "string",
              "enum": [
                "play_distribution",
                "belief_trajectory",
                "resource_burn",
                "graph_event_frequency",
                "drive_outcome"
              ]
            },
            "event_tag": { "type": "string", "minLength": 1 },
            "graph_card_id": { "type": "string", "pattern": "^redzone\\." },
            "observed_value": {
              "oneOf": [
                { "type": "number" },
                { "type": "string" },
                { "type": "boolean" },
                { "type": "object" }
              ]
            },
            "threshold": {
              "oneOf": [
                { "type": "number" },
                { "type": "string" },
                { "type": "boolean" },
                { "type": "object" }
              ]
            },
            "parameter": {
              "type": "string",
              "enum": [
                "risk_tolerance",
                "adaptation_speed",
                "screen_trigger_confidence",
                "explosive_shot_tolerance",
                "run_pass_tendency",
                "disguise_sensitivity",
                "pressure_frequency",
                "counter_repeat_tolerance"
              ]
            },
            "direction": {
              "type": "string",
              "enum": ["increase", "decrease", "set"]
            }
          }
        },
        "rendered": {
          "type": "string",
          "description": "Generated only from template_id and arguments; not authored as free prose.",
          "minLength": 1,
          "maxLength": 180
        }
      }
    }
  },
  "allOf": [
    {
      "if": {
        "properties": { "direction": { "const": "set" } },
        "required": ["direction"]
      },
      "then": {},
      "else": {
        "not": { "required": ["target_value"] }
      }
    }
  ]
}
```

## Worked Examples

Each example targets one current adaptive agent parameter. The `rationale.rendered` sentence is generated from `rationale.template_id` and `rationale.arguments`; it is shown for readback only.

```json
[
  {
    "tweak_id": "twk_adaptation_speed_run_fit_001",
    "parameter": "adaptation_speed",
    "direction": "increase",
    "magnitude": "small",
    "evidence": {
      "signal": "belief_trajectory",
      "observed_value": {
        "belief": "run_fit_aggression",
        "value": 0.61,
        "event_tag": "wide_zone_constrained"
      },
      "threshold": {
        "agent_gate": "stress_threshold",
        "code_ref": "agents/adaptive_offense.py:23"
      },
      "play_indices": [1]
    },
    "source": {
      "graph_card_id": "redzone.outside_zone_vs_bear.v1"
    },
    "rationale": {
      "template_id": "belief_event_crossed_threshold",
      "arguments": {
        "play_indices": [1],
        "signal": "belief_trajectory",
        "event_tag": "wide_zone_constrained",
        "graph_card_id": "redzone.outside_zone_vs_bear.v1",
        "observed_value": { "belief": "run_fit_aggression", "value": 0.61 },
        "threshold": { "agent_gate": "stress_threshold" },
        "parameter": "adaptation_speed",
        "direction": "increase"
      },
      "rendered": "Play 1 produced wide_zone_constrained and run_fit_aggression reached 0.61, so increase adaptation_speed."
    }
  },
  {
    "tweak_id": "twk_screen_trigger_bait_001",
    "parameter": "screen_trigger_confidence",
    "direction": "decrease",
    "magnitude": "small",
    "evidence": {
      "signal": "graph_event_frequency",
      "observed_value": {
        "event_tag": "screen_baited",
        "count": 1,
        "screen_trap_risk_after": 0.49
      },
      "threshold": {
        "event_count": 1,
        "agent_gate": "pressure_threshold",
        "code_ref": "agents/adaptive_offense.py:25"
      },
      "play_indices": [2]
    },
    "source": {
      "graph_card_id": "redzone.screen_vs_simulated_pressure.v1"
    },
    "rationale": {
      "template_id": "event_count_crossed_threshold",
      "arguments": {
        "play_indices": [2],
        "signal": "graph_event_frequency",
        "event_tag": "screen_baited",
        "graph_card_id": "redzone.screen_vs_simulated_pressure.v1",
        "observed_value": { "count": 1, "screen_trap_risk_after": 0.49 },
        "threshold": { "event_count": 1 },
        "parameter": "screen_trigger_confidence",
        "direction": "decrease"
      },
      "rendered": "Play 2 produced screen_baited once, so decrease screen_trigger_confidence."
    }
  },
  {
    "tweak_id": "twk_explosive_shot_capped_001",
    "parameter": "explosive_shot_tolerance",
    "direction": "decrease",
    "magnitude": "medium",
    "evidence": {
      "signal": "graph_event_frequency",
      "observed_value": {
        "event_tag": "explosive_window_capped",
        "count": 1,
        "offense_call": "vertical_shot"
      },
      "threshold": {
        "agent_gate": "explosive_shot_tolerance > 0.6",
        "code_ref": "agents/example_agent.py:39"
      },
      "play_indices": [4]
    },
    "source": {
      "graph_card_id": "redzone.vertical_vs_two_high.v1"
    },
    "rationale": {
      "template_id": "event_count_crossed_threshold",
      "arguments": {
        "play_indices": [4],
        "signal": "graph_event_frequency",
        "event_tag": "explosive_window_capped",
        "graph_card_id": "redzone.vertical_vs_two_high.v1",
        "observed_value": { "count": 1, "offense_call": "vertical_shot" },
        "threshold": { "event_count": 1 },
        "parameter": "explosive_shot_tolerance",
        "direction": "decrease"
      },
      "rendered": "Play 4 produced explosive_window_capped after vertical_shot, so decrease explosive_shot_tolerance."
    }
  },
  {
    "tweak_id": "twk_disguise_sensitivity_bait_001",
    "parameter": "disguise_sensitivity",
    "direction": "increase",
    "magnitude": "small",
    "evidence": {
      "signal": "graph_event_frequency",
      "observed_value": {
        "event_tag": "screen_baited",
        "count": 1,
        "defense_call": "simulated_pressure"
      },
      "threshold": {
        "agent_gate": "disguise_sensitivity >= 0.5",
        "code_ref": "agents/adaptive_defense.py:32"
      },
      "play_indices": [2]
    },
    "source": {
      "graph_card_id": "redzone.screen_vs_simulated_pressure.v1"
    },
    "rationale": {
      "template_id": "event_count_crossed_threshold",
      "arguments": {
        "play_indices": [2],
        "signal": "graph_event_frequency",
        "event_tag": "screen_baited",
        "graph_card_id": "redzone.screen_vs_simulated_pressure.v1",
        "observed_value": { "count": 1, "defense_call": "simulated_pressure" },
        "threshold": { "event_count": 1 },
        "parameter": "disguise_sensitivity",
        "direction": "increase"
      },
      "rendered": "Play 2 produced screen_baited from simulated_pressure, so increase disguise_sensitivity."
    }
  },
  {
    "tweak_id": "twk_pressure_frequency_disguise_burn_001",
    "parameter": "pressure_frequency",
    "direction": "decrease",
    "magnitude": "small",
    "evidence": {
      "signal": "resource_burn",
      "observed_value": {
        "defense_call": "simulated_pressure",
        "defense_cost": { "rush": 2, "coverage": 2, "box": 1, "disguise": 3 },
        "defense_remaining": { "rush": 12, "coverage": 17, "box": 12, "disguise": 11 }
      },
      "threshold": {
        "single_play_disguise_cost": 3,
        "code_ref": "graph/redzone_v0/resource_constraints.json:129"
      },
      "play_indices": [2]
    },
    "source": {
      "graph_card_id": "redzone.screen_vs_simulated_pressure.v1"
    },
    "rationale": {
      "template_id": "resource_burn_crossed_threshold",
      "arguments": {
        "play_indices": [2],
        "signal": "resource_burn",
        "event_tag": "screen_baited",
        "graph_card_id": "redzone.screen_vs_simulated_pressure.v1",
        "observed_value": { "defense_call": "simulated_pressure", "disguise_cost": 3 },
        "threshold": { "single_play_disguise_cost": 3 },
        "parameter": "pressure_frequency",
        "direction": "decrease"
      },
      "rendered": "Play 2 spent 3 disguise on simulated_pressure, so decrease pressure_frequency."
    }
  },
  {
    "tweak_id": "twk_counter_repeat_stress_001",
    "parameter": "counter_repeat_tolerance",
    "direction": "decrease",
    "magnitude": "small",
    "evidence": {
      "signal": "graph_event_frequency",
      "observed_value": {
        "event_tag": "coverage_switch_stress",
        "count": 2,
        "offense_call": "bunch_mesh"
      },
      "threshold": {
        "agent_gate": "counter_threshold",
        "high_tolerance_threshold": 2,
        "code_ref": "agents/adaptive_defense.py:22"
      },
      "play_indices": [3, 4]
    },
    "source": {
      "graph_card_id": "redzone.bunch_mesh_vs_match.v1"
    },
    "rationale": {
      "template_id": "event_count_crossed_threshold",
      "arguments": {
        "play_indices": [3, 4],
        "signal": "graph_event_frequency",
        "event_tag": "coverage_switch_stress",
        "graph_card_id": "redzone.bunch_mesh_vs_match.v1",
        "observed_value": { "count": 2, "offense_call": "bunch_mesh" },
        "threshold": { "event_count": 2 },
        "parameter": "counter_repeat_tolerance",
        "direction": "decrease"
      },
      "rendered": "Plays 3 and 4 produced coverage_switch_stress twice, so decrease counter_repeat_tolerance."
    }
  }
]
```

Field-source checks:

- Event `tag`, `graph_card_id`, `description`, and `counters` are emitted by `engine/coachbench/interaction_engine.py:28,35,38,39,40`.
- Public and side-specific events are carried into observations by `engine/coachbench/observations.py:46,58,64,72,79,87`.
- Belief fields used in examples are emitted through `belief_after` at `engine/coachbench/observations.py:75,90` and are updated from `graph/redzone_v0/belief_model.json:5,23,31,47,67`.
- Resource evidence maps to `resource_budget_snapshot` from `engine/coachbench/engine.py:187,199` and graph costs from `graph/redzone_v0/resource_constraints.json:30,92`.
- Graph event sources used above exist at `graph/redzone_v0/interactions.json:4,40,75,111,192`.

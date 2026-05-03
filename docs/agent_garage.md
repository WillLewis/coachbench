# Agent Garage

Agent Garage is the no-code entry point for CoachBench. It lets a player create a visible coordinator profile that compiles into legal agent behavior.

## Requirements

```text
visible config only
no hidden personality overrides
maps to legal action policies
cannot access hidden fields
cannot spend impossible resources
```

## P0 controls

```text
offensive archetype
defensive archetype
risk tolerance
adaptation speed
pressure-punish threshold
screen trigger confidence
explosive-shot tolerance
run/pass tendency
disguise sensitivity
counter-repeat tolerance
```

## P0 output

Agent Garage writes a config object included in replay JSON under `agent_garage_config`.

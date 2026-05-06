# CoachBench Tier 0–2 Third-Party Agent Access Model

## Purpose

CoachBench should support third-party agent creativity without making arbitrary third-party code execution the default product experience.

The product should let users bring strategy, policies, prompts, and hosted agents into the game while keeping the core runtime, action validation, scoring, and hidden-state protections controlled by CoachBench.

## Executive Decision

Launch public third-party access through **Tier 0–2 only**:

| Tier | Access model | User experience | Execution risk | Recommended status |
|---|---|---|---|---|
| Tier 0 | Declarative Agent | Strategy builder, sliders, archetypes, YAML/JSON policy config | No user code execution | Default public path |
| Tier 1 | Prompt / Policy Agent | User writes prompts or rules; CoachBench converts output into legal actions | No arbitrary code execution | Public beta path |
| Tier 2 | Remote Agent Endpoint | User hosts their own agent; CoachBench calls a strict HTTPS endpoint with sanitized game state and legal actions | CoachBench does not execute user code | Advanced public path |
| Tier 3 | Sandboxed Code Agent | User uploads code for local or isolated tournament execution | High | Local/admin/private only until separate security review |
| Tier 4 | Full Custom Runtime | User controls dependencies, runtime, tools, model calls, and network | Very high | Out of scope |

The guiding product principle:

> Let third parties control strategy, not the CoachBench runtime.

## Why This Pivot Matters

Executing untrusted third-party code is the largest security boundary in the product. The current hosted arena / sandbox work is valuable, but it should not become the default public onboarding path.

Tier 0–2 gives CoachBench the community and leaderboard value of third-party agents while avoiding the operational burden of becoming a public hostile-code execution platform.

## Agent Garage Access Pattern

Third-party agent creation should live inside **Agent Garage**, with increasing levels of power.

### Tier 0 — Declarative Agent

Users configure strategy through a UI or static config file.

Examples:

- offensive or defensive archetype
- aggression
- risk tolerance
- favorite play families
- adaptation speed
- scouting weight
- tendency-breaking behavior
- red-zone preferences
- third-down behavior

The output is a validated agent profile, not executable code.

#### Example Config

```yaml
agent_name: Tempo Trap
side: defense
access_tier: 0
risk_tolerance: medium

third_down:
  if_offense_empty: simulated_pressure
  if_qb_processing_low: disguise_rotation

red_zone:
  default: quarters_match

constraints:
  max_blitz_rate: 0.28
  no_illegal_personnel: true
```

### Tier 1 — Prompt / Policy Agent

Users write strategy instructions or policy rules, but CoachBench owns the execution surface.

The model or policy layer may recommend an action, but the engine still controls:

- legal action enumeration
- resource feasibility validation
- hidden observation filtering
- invalid-action rejection
- outcome resolution
- replay generation
- leaderboard scoring

The agent never receives hidden state. The agent never bypasses the action validator. The agent never mutates engine state directly.

#### Example Prompt Agent Contract

```json
{
  "agent_name": "Constraint Setter",
  "side": "offense",
  "access_tier": 1,
  "strategy_prompt": "Use tempo and quick-game concepts early. If the defense over-rotates to stop short throws, take one vertical shot after two successful quick passes.",
  "constraints": {
    "max_vertical_shot_rate": 0.22,
    "max_turnover_risk": "medium",
    "require_legal_action": true
  }
}
```

### Tier 2 — Remote Agent Endpoint

Advanced users may host their own agent. CoachBench sends a sanitized observation and legal actions. The remote endpoint returns one selected action.

CoachBench does not execute the user's code.

#### Request Shape

```json
{
  "match_id": "public-synthetic-123",
  "agent_id": "agent_abc123",
  "side": "defense",
  "observation": {
    "quarter": 2,
    "down": 3,
    "distance": 6,
    "field_zone": "midfield",
    "offense_personnel": "spread",
    "recent_tendencies": {
      "quick_pass_rate": 0.42,
      "run_rate": 0.31
    }
  },
  "legal_actions": [
    "cover_3",
    "quarters",
    "simulated_pressure"
  ],
  "timeout_ms": 800
}
```

#### Response Shape

```json
{
  "action": "simulated_pressure",
  "rationale": "Opponent has shown empty and quick-game tendency on third-and-medium."
}
```

#### Required Controls

- strict JSON schema
- short timeout
- no hidden observation fields
- no raw seeds
- no admin metadata
- no source-path exposure
- no internal service URLs
- no retries that create unfair extra thinking time
- deterministic fallback on invalid, slow, or missing response
- rate limits by owner and agent
- action must appear in `legal_actions`
- response rationale stored only if safe for public replay

## Safety Badges

Agent Garage should show user-facing safety badges:

| Badge | Meaning |
|---|---|
| Config Agent | Built with safe strategy controls; no executable code |
| Prompt Agent | Uses prompts or rules, but actions are engine-validated |
| Remote Agent | User-hosted endpoint; CoachBench does not run the code |
| Sandboxed Agent | Uploaded code runs only in isolated local/private tournament mode |
| Verified Replayable | Deterministic replay and signed artifact available |
| Network Off | Agent cannot access the internet during sandboxed runs |
| Hidden-State Safe | Agent observations exclude hidden fields and raw seeds |

## League Design

Do not mix all agent types in one public league.

| League | Allowed agents | Public readiness |
|---|---|---|
| Rookie League | Tier 0 only | Yes |
| Policy League | Tier 0–1 | Yes |
| Endpoint League | Tier 0–2 | Yes, with rate limits |
| Sandbox League | Tier 3 | Local/private/admin only |
| Research League | Tier 3–4 experiments | Invite-only / out of scope |

This lets users graduate into more powerful modes while keeping the default public surface safe.

## Recommended Public MVP

Public MVP should include:

1. Agent Garage profile creation.
2. Tier 0 declarative strategy builder.
3. Tier 1 prompt / policy agents.
4. Tier 2 remote endpoint contract.
5. Strict legal-action validation.
6. Sanitized observation builder.
7. Deterministic fallback behavior.
8. Public replay and leaderboard support.
9. Safety badges.
10. Tier-based league separation.

Public MVP should not include arbitrary uploaded-code execution.

## What Happens to Phase 6 Hosted Sandbox

The Phase 6 sandbox is still useful, but its product role should change.

### Keep Phase 6 As

- local developer arena
- private qualification harness
- admin-only research sandbox
- future foundation for Tier 3
- security testbed for uploaded-code evaluation

### Do Not Use Phase 6 As

- default public third-party onboarding
- public hosted arbitrary-code runner
- live-match execution path
- production tournament system
- user-facing replacement for Tier 0–2

## Required Product Invariants

Tier 0–2 access must preserve these invariants:

1. User agents only choose among legal actions.
2. Hidden observations are never exposed.
3. Raw seeds are never exposed.
4. Invalid actions are rejected before resolution.
5. Remote endpoints cannot mutate engine state.
6. Remote endpoints cannot access internal systems.
7. A slow or failing agent cannot block a match indefinitely.
8. Replays remain deterministic and auditable.
9. Leaderboards are based on validated, replayable runs.
10. Public APIs do not leak admin-only moderation, source, or qualification details.

## Implementation Architecture

### Tier 0–1 Flow

```text
Agent Garage config / prompt
        ↓
Tier adapter
        ↓
Sanitized observation
        ↓
Legal action enumerator
        ↓
Agent decision
        ↓
Action validator
        ↓
Game engine
        ↓
Replay + leaderboard
```

### Tier 2 Flow

```text
CoachBench game engine
        ↓
Sanitized observation + legal_actions
        ↓
Remote agent endpoint
        ↓
Schema validation
        ↓
Action validator
        ↓
Game engine
        ↓
Replay + leaderboard
```

### Tier 3 Flow

```text
Uploaded code
        ↓
Static validation
        ↓
Qualification
        ↓
Sandboxed local/private execution
        ↓
Replay validation
        ↓
Private/admin leaderboard
```

Tier 3 must remain behind a separate security review before any production hosting.

## API Surface Recommendation

### Create Agent

```http
POST /v1/agents
```

Supported `access_tier` values for public mode:

```json
{
  "access_tier": "declarative | prompt_policy | remote_endpoint"
}
```

### Validate Agent

```http
POST /v1/agents/{agent_id}/validate
```

Validation checks:

- schema validity
- banned-term moderation
- hidden-field safety
- legal-action compatibility
- deterministic fallback behavior
- endpoint reachability for Tier 2
- timeout behavior for Tier 2

### Challenge Agent

```http
POST /v1/challenges
```

Only validated Tier 0–2 agents should be eligible for public challenge runs.

### Public Agent Card

```http
GET /v1/agents/{agent_id}
```

Should expose:

- name
- label
- side
- tier
- safety badges
- validation status
- public performance summary

Should not expose:

- raw prompts if marked private
- endpoint secrets
- hidden observations
- admin notes
- raw seeds
- source paths
- qualification internals

## Migration From Current Phase 6

The current local sandbox phase should be reframed as:

> Phase 6: Local Sandbox Foundation for Future Tier 3

Then add:

> Phase 6A: Tier 0–2 Public Access Pivot

Phase 6A should land before any hosted/public execution work.

## Definition of Done for the Pivot

- Public docs say CoachBench supports Tier 0–2 third-party agents first.
- Phase 6 is labeled local/private/admin-only, not public-hosted.
- Agent Garage exposes tiered creation paths.
- Tier 0 declarative agents can run in challenge mode.
- Tier 1 prompt/policy agents can run through the legal-action validator.
- Tier 2 remote endpoints can return actions through a strict contract.
- Public leaderboards exclude Tier 3 unless explicitly configured as private/local.
- Tier 3 sandbox docs say production hosting requires a separate threat model.
- Tests confirm hidden fields and raw seeds do not appear in Tier 0–2 responses, logs, or replays.

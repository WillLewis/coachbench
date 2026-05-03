# CoachBench Final Plan

## 0. Product frame

CoachBench is a football-inspired adversarial-agent arena for short red-zone strategy contests. Offensive and defensive coordinator agents compete through simultaneous legal play calls, scarce tactical resources, partial observability, in-game belief updates, and seeded reproducibility. Viewers can inspect how an agent discovered, exploited, or failed to counter an edge.

Public line:

> Can your agent discover the edge before the opponent adjusts?

The first public artifact should feel like:

```text
broadcast-style red-zone replay
+ agent debugger
+ tactical graph explorer
+ local multi-agent benchmark
+ player-facing improvement loop
```

The product is not a licensed football game, team simulator, real-league prediction product, or gambling product. It is a football-inspired strategy benchmark using fictional teams, fictional roster profiles, symbolic concepts, and inspectable logic.

## 1. North star goals

CoachBench should make four audiences care.

### 1.1 AI/ML practitioners

They should see a real benchmark:

```text
partial observability
simultaneous actions
seeded reproducibility
agent-vs-agent interaction
baseline/adaptive agent teams
belief updates
agentic metrics
local evaluation harness
```

### 1.2 Football/data people

They should see football-native logic:

```text
red-zone context
concept families
resource tradeoffs
sequencing
counters
visible tactical events
graph-backed explanations
```

### 1.3 Developer/platform users

They should see a forkable system:

```text
read graph cards
run local evaluation
write an agent
inspect replay JSON
compare across seeds
add or test graph cards
```

### 1.4 Sports-gaming users

They should see a repeatable improvement loop:

```text
enter through Agent Garage
run a short challenge
watch the Film Room
adjust the agent
try the Daily Slate
improve over time
```

## 2. Locked principles

### 2.1 Graph first, not fake generated strategy

The simulator must not rely on a language model inventing football truth. The source of truth is the strategy graph plus deterministic engine logic.

```text
Football Strategy Graph
        ↓
Legal Action Enumerator
        ↓
Resource-Constrained Strategy Engine
        ↓
Concept Interaction Engine
        ↓
Outcome + Tactical Event Log
        ↓
Agent Observation + Belief Update
        ↓
Replay UI + Evaluation Harness
        ↓
Agent Garage / Film Room / Daily Slate
```

Language models may summarize structured events, but they do not decide tactical truth.

### 2.2 Red zone first

Start with short red-zone drives because they are compact, high-leverage, easy to replay, and easy to understand.

Initial scenario:

```text
Ball: opponent 20–25 yard line
Drive length: up to 8 plays
Mode: simultaneous offense/defense calls
Outcome: touchdown / field goal / turnover / failed drive / expected-value result
```

### 2.3 Legal actions are prevented, not penalized

The engine should make illegal actions impossible wherever possible.

Required layers:

```text
Layer 1 — Legal action enumerator
  Engine exposes only currently legal choices.

Layer 2 — Action schema validator
  Submitted actions must match the required schema.

Layer 3 — Resource feasibility validator
  Submitted actions must fit the current tactical budget.

Layer 4 — Execution boundary
  Invalid third-party submissions are rejected before play resolution.
```

Invalid actions should not become football penalties or odd simulated outcomes. Invalid-action rate can exist as a developer-quality metric, but not as a football scoring mechanic.

For local third-party agents, invalid submissions are rejected before resolution, logged in `validation_result`, counted in `invalid_action_count`, and replaced by a deterministic validator-owned safe fallback from the current legal action set. The fallback is not treated as the agent's tactical truth; it is validation handling so the replay and metrics remain inspectable.

### 2.4 Resource constraints are non-negotiable

No call can have every advantage at once.

Examples:

```text
Zero pressure:
  + pressure speed
  + turnover volatility
  - coverage bodies
  - screen safety
  - explosive protection

Two-high shell:
  + explosive prevention
  - box count
  - some run-fit strength

Max protection:
  + pass protection
  - route count
  - spacing stress

Bunch/stack:
  + communication stress
  + switch/passoff tests
  - compressed red-zone spacing
  - tendency signal if repeated
```

Every strong tactic needs a cost, and every dominant interaction needs a counter.

### 2.5 Partial observability now, scouting and Film Room now as player-facing guidance

The benchmark loop uses partial observability and in-game inference from the start. Scouting/Film Room is included as player-facing guidance, but it must be carefully scoped.

P0/P1 includes:

```text
post-match Film Room
structured scouting-style notes generated from observed events
turning-point analysis
recommended agent adjustments
no hidden real-world scouting data
no licensed team or player references
```

Later phases may include:

```text
pre-drive fictional scouting cards
stale or noisy fictional reports
hidden fictional matchup traits
belief calibration against private truth
```

### 2.6 Coach archetypes are accessibility wrappers, not hidden benchmark truth

Coach archetypes make the game more accessible. They are allowed early as Agent Garage choices and UI labels, provided the underlying benchmark logic remains explicit.

Allowed early:

```text
Efficiency Optimizer
Aggressive Shot-Taker
Misdirection Artist
Run-Game Builder
Coverage Shell Conservative
Pressure-Look Defender
Disguise Specialist
Man-Coverage Bully
```

Required constraint:

```text
Each archetype maps to visible parameters.
No hidden personality system may override legal action generation, graph rules, or resource constraints.
```

### 2.7 No licensed league/team/player references

The plan must not depend on any licensed league, team, player, logo, trademarked ratings product, or official tracking product.

Use neutral language:

```text
football-inspired
gridiron strategy
red-zone benchmark
coordinator agents
fictional roster templates
publicly permissible aggregate priors
```

Avoid:

```text
real teams
real players
league logos
official ratings products
licensed pro-league references
brand-adjacent hashtags
```

### 2.8 Transparent and forkable

Long-term value comes from a repo where people can inspect and test the benchmark.

Eventually users should be able to:

```text
read the graph
run local eval
write an agent
watch replay
fork graph cards
submit improvements
compare agents across seeds
```

Hosted execution comes later because sandboxing third-party code is a serious security project.

## 3. P0 product boundary

### P0 includes

```text
red-zone drives only
fictional/equal rosters only
symbolic football concepts
simultaneous offensive/defensive calls
legal action enumeration
resource constraints
strategy graph v0
concept interaction engine
deterministic seeded replay
two agent teams
interaction matrix
Agent Garage v0
Film Room v0
Daily Slate v0
static polished replay UI
local run/eval scripts
graph-card documentation
```

### P0 does not include

```text
real teams
real players
licensed logos
official ratings
full 11-player geometry
real route stems
movement tracking
full-game clock strategy
substitutions
weather
fatigue
injuries
franchise mode
hosted third-party execution
cash contests or wagering
```

This boundary keeps the first version from becoming a football game instead of an adversarial-agent benchmark and strategy arena.

## 4. Benchmark contract

### 4.1 Episode contract

```text
episode_id
graph_version
engine_version
seed
start_yardline
max_plays
down
distance
score_mode
drive_terminal_condition
```

Terminal conditions:

```text
touchdown
field goal attempt / field goal result
turnover
turnover on downs
max plays reached
validation failure
```

### 4.2 Action contract

Each play has:

```text
offense_action
defense_action
legal_action_set_id
resource_budget_snapshot
validation_result
```

Offense action fields:

```text
personnel_family
formation_family
motion_family
concept_family
protection_family
risk_level
constraint_tag
```

Defense action fields:

```text
personnel_family
front_family
coverage_family
pressure_family
disguise_family
matchup_focus
risk_level
constraint_tag
```

For P0, these are symbolic categories, not full playbook details.

### 4.3 Observation contract

Agents receive only allowed information.

Offense can observe:

```text
game state
own prior calls
own resource usage
post-play tactical events revealed to offense
outcome
belief-state update
```

Defense can observe:

```text
game state
own prior calls
own resource usage
post-play tactical events revealed to defense
outcome
belief-state update
```

P0 does not expose pre-commitment shell, alignment, personnel, formation, or motion hints because the starter engine has no separate commit/reveal phase yet. Neither side receives the opponent's full private action before committing. Post-play learning is event-mediated through graph events with explicit side visibility.

### 4.4 Replay contract

Replay JSON includes:

```text
episode metadata
seed/hash
graph version
engine version
play-by-play state
offense call
defense call
visible observations
resource tradeoffs
tactical events
graph card references
belief updates
Film Room notes
outcomes
post-drive summary
```

The replay should distinguish:

```text
public viewer fields
agent-observed fields
hidden engine fields
debug-only fields
```

### 4.5 Scoring contract

Core football-inspired metrics:

```text
points per drive
touchdown rate
success rate
negative-play rate
turnover rate
expected-value result
```

Agentic metrics:

```text
adaptation value
exploitation latency
adjustment latency
successful counter rate
bait success rate
tendency predictability
belief calibration error
robustness across seeds
```

Invalid-action rate remains a validation/developer metric, not a football score.

## 5. Agent Garage

Agent Garage is the player-facing entry point. It makes coordinator-agent design accessible without requiring code.

### 5.1 User promise

```text
Build a coordinator profile.
Run it against a short red-zone challenge.
Study the Film Room.
Tune and try again.
```

### 5.2 Controls

Agent Garage exposes visible parameters:

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
resource conservation
```

### 5.3 Archetype examples

Offense:

```text
Efficiency Optimizer:
  favors success rate, quick game, and lower variance

Aggressive Shot-Taker:
  takes more vertical attempts and accepts volatility

Misdirection Artist:
  uses screens, boots, and tendency-breaking

Run-Game Builder:
  uses run sequencing to unlock play-action and constraint calls
```

Defense:

```text
Coverage Shell Conservative:
  limits explosives and concedes some underneath value

Pressure-Look Defender:
  shows pressure and varies true pressure vs simulated pressure

Disguise Specialist:
  uses late rotation and trap looks to attack assumptions

Man-Coverage Bully:
  trusts coverage, loads the box, and accepts matchup risk
```

### 5.4 Guardrails

```text
Agent Garage writes a transparent config.
Configs compile into legal agent policies.
No archetype can bypass the legal action enumerator.
No archetype can spend impossible resources.
No archetype can access hidden engine fields.
```

## 6. Film Room

Film Room is the retention-critical feedback screen. It turns a match result into a reason to adjust and retry.

### 6.1 Required outputs

```text
why you won or lost
turning point
belief mistake or successful inference
resource mistake or successful tradeoff
best counter missed
opponent adjustment
suggested tweak
graph-card explanation
```

### 6.2 Example note

```text
Turning point: Play 4

Your offense treated the pressure look as a true pressure signal.
The defense used simulated pressure and trap coverage.
Your screen trigger fired too early.

Suggested adjustment:
Lower screen trigger confidence until pressure is confirmed twice,
or pair pressure looks with quick-game/flood alternatives.
```

### 6.3 Rule

Film Room should summarize structured event logs. It should not invent unseen tactics, private truth, or licensed references.

## 7. Daily Slate

Daily Slate gives users a repeatable reason to return.

### 7.1 User promise

```text
A short red-zone slate drops on a fixed cadence.
Everyone faces the same fictional challenge seeds.
Users tune agents, submit locally or later through hosted eval, and compare results.
```

### 7.2 P0 local version

```text
3 fixed seeds
same fictional roster profile
same baseline opponent set
local results report
engine-generated replays
Film Room summary per seed
```

### 7.3 Later hosted version

```text
locked submission window
hidden official seeds
leaderboard reveal
meta report
season standings
```

Daily Slate must remain non-wagering and focused on strategy, learning, and benchmark comparison.

## 8. P0 action vocabulary

Keep the first vocabulary compact.

### Offense concepts

```text
inside_zone
outside_zone
power_counter
quick_game
bunch_mesh
rpo_glance
play_action_flood
vertical_shot
screen
bootleg
```

### Defense calls

```text
base_cover3
cover3_match
quarters_match
cover1_man
two_high_shell
zero_pressure
simulated_pressure
bear_front
trap_coverage
redzone_bracket
```

This is enough to show sequencing, counters, resource tradeoffs, partial observability, belief updates, and adaptive behavior.

## 9. Agent teams

The plan needs explicit agent teams. The baseline ladder alone is not enough unless those baselines are organized into teams and tested against each other.

### 9.1 Team definition

```text
offensive coordinator agent
defensive coordinator agent
team config
legal action policy
evaluation metadata
replay/export compatibility
```

### 9.2 Initial two teams

Team A — Static Baseline:

```text
OC: static situational offense
DC: static situational defense
Purpose: replacement-level benchmark, sanity check, simple comparison point
```

Team B — Adaptive Counter:

```text
OC: tendency-tracking adaptive offense
DC: adaptive counter/disguise defense
Purpose: prove adaptation matters, test sequencing, test graph interaction quality
```

### 9.3 Interaction matrix

Run:

```text
Team A OC vs Team A DC
Team B OC vs Team A DC
Team A OC vs Team B DC
Team B OC vs Team B DC
```

This answers:

```text
Does adaptive offense outperform static offense against the same defense?
Does adaptive defense suppress static offense?
Does adaptive-vs-adaptive produce nontrivial sequencing?
Does the graph create obvious exploits or degenerate strategies?
```

## 10. Graph cards

Every important interaction should have a graph card with:

```text
id
name
preconditions
resource constraints
tactical events
outcome modifiers
counters
limitations
```

Graph validation requirements:

```text
No interaction has only upside unless explicitly marked rare.
Every strong tactic has at least one counter.
Every resource-heavy call spends constrained resources.
Every tactical event cites a graph card.
Every graph card declares limitations.
Every modifier stays within allowed numeric bounds.
No graph card references licensed teams, players, or leagues.
```

## 11. UI plan

The public demo should feel like:

```text
broadcast gamecast
+ agent debugger
+ tactical graph explorer
+ Film Room
+ Agent Garage
+ Daily Slate entry point
```

Required panels:

```text
hero / demo framing
Agent Garage config card
score + drive state
field visualization
play timeline
offense call card
defense call card
visible observation card
tactical event log
belief-state bars
resource tradeoff panel
graph interaction card
Film Room panel
Daily Slate card
post-drive insight summary
```

Each play click should update:

```text
field position
down/distance
offense call
defense call
visible shell/alignment
resource usage
event tags
belief values
graph-card rationale
agent notes
outcome
```

## 12. Metrics

Core metrics:

```text
points per drive
touchdown rate
success rate
negative-play rate
turnover rate
expected-value result
red-zone efficiency
```

Agentic metrics:

```text
adaptation value
exploitation latency
adjustment latency
successful counter rate
bait success rate
tendency predictability
belief calibration error
robustness across seeds
```

Player-retention metrics:

```text
Agent Garage config completion
first match completion
Film Room opened
tweak after Film Room
rematch after tweak
Daily Slate completion
repeat Daily Slate participation
```

Headline metric:

```text
Agent Value Over Replacement Playcaller
```

## 13. Phase plan

### Phase 0A — Spec Lock

Deliverables:

```text
benchmark contract
episode schema
action schema
observation schema
replay schema
scoring schema
P0 action vocabulary
resource-budget rules
graph-card format
product non-goals
license-safe naming rules
Agent Garage v0 spec
Film Room v0 spec
Daily Slate v0 spec
Backlog section
```

Exit criteria:

```text
everyone can describe one episode
everyone knows what agents can and cannot see
everyone knows what actions are legal
everyone knows what replay JSON must contain
P0 scope is bounded
```

Estimated effort: 2–3 person-days.

### Phase 0B — Static Schema/UI Proof

Deliverables:

```text
hand-authored replay JSON
zero-dependency static UI
clickable play timeline
Agent Garage display shell
Film Room display shell
Daily Slate display shell
field view
call cards
resource tradeoff display
graph-card panel
belief-state display
post-drive summary shell
```

Constraint:

```text
The static replay validates UI and schema only.
It is not claimed as an engine-generated benchmark result.
```

Estimated effort: 4–6 person-days.

### Phase 1 — Real P0 Engine

Deliverables:

```text
legal action enumerator
action schema validator
resource feasibility validator
concept interaction engine
outcome resolution engine
observation engine
belief update engine v0
event log engine
Film Room structured note generator
deterministic replay export
local run script
```

Exit criteria:

```text
same seed produces same replay
agents receive only allowed observations
illegal actions are rejected before resolution
resource-impossible calls are rejected before resolution
graph interactions drive tactical event logs
engine-generated replay matches replay schema
Film Room notes are derived from events
```

Estimated effort: 9–14 person-days.

### Phase 1.5 — Agent Team Suite / Interaction Matrix

Deliverables:

```text
Team A static OC
Team A static DC
Team B adaptive OC
Team B adaptive DC
team config schema
local matchup runner
A/B interaction matrix
best-of-N red-zone evaluation
seeded replay export
simple comparison report
```

Estimated effort: 4–7 person-days.

### Phase 1.75 — Benchmark Hardening

Deliverables:

```text
graph invariant tests
replay schema tests
deterministic seed tests
legal-action tests
resource-budget tests
golden seed selection
calibration sanity checks
replay diff tests
baseline comparison report
```

Estimated effort: 4–6 person-days.

### Phase 2 — Polished Public Demo

Deliverables:

```text
high-fidelity replay UI
field animation
belief/resource panels
interactive Agent Garage v0
Film Room v0
Daily Slate local view
graph-card explorer
post-drive insight summary
engine-generated showcase replay
README-style overview
one-command local demo
recorded demo/GIF or short video
human-readable agent labels
```

Estimated effort: 6–10 person-days.

### Phase 3 — Local Agent Ecosystem

Deliverables:

```text
agent template
agent validator
local gauntlet
best-of-N runner
tournament runner
example custom agent
local replay export
developer docs
```

Estimated effort: 6–10 person-days.

### Phase 4 — Fictional Roster Budget

Deliverables:

```text
fictional roster-budget schema
position-group trait sliders
balanced templates
budget validation
mirrored-seed evaluation
budget-mode local leaderboard
UI panel for owned strengths/weaknesses
```

Estimated effort: 5–8 person-days.

### Phase 5 — Scouting / Hidden Edge Layer

Deliverables:

```text
fictional scouting card schema
incomplete scouting reports
stale or noisy scouting signals
hidden fictional matchup traits
belief calibration against private truth
pre-drive planning observations
post-drive inference report
```

Estimated effort: 7–12 person-days.

### Phase 6 — Hosted Sandbox / Arena

Deliverables:

```text
agent upload flow
static validation
qualification suite
sandboxed runner
agent registry
challenge matches
hidden-seed leaderboard
worker isolation
admin moderation tools
logs and replay review
```

Estimated effort: 15–30+ person-days.

### Phase 7 — Fictional Team Templates / Chaos Modes

Deliverables:

```text
fictional team-style templates
fictional roster identities
fatigue-like conditions
weather-like conditions
availability variance
longer-form game modes
season/tournament narratives
casual story mode
```

Estimated effort: 12–25+ person-days.

## 14. Backlog

These ideas are intentionally parked until the core loop is validated.

### 14.1 Rookie Pools

Potential value:

```text
protect beginners
reduce early churn
separate starter-agent users from expert coders
make leaderboard participation less intimidating
```

Open questions:

```text
What qualifies a user as rookie?
How long should protection last?
Can a strong user smurf with a new agent?
Should Rookie Pools exist before hosted play?
```

### 14.2 Social Share Features

Potential value:

```text
share replay links
challenge friends
publish agent cards
invite private matches
increase viral surface area
```

Open questions:

```text
Do we need accounts first?
Can static replay export handle early sharing?
What moderation risk exists?
Should private challenges wait for hosted sandbox?
```

## 15. Realistic build-time view

Fastest credible public proof:

```text
Phase 0A Spec Lock: 2–3 days
Phase 0B Static UI/Schema Proof: 4–6 days
Phase 1 Real Engine: 9–14 days
Phase 1.5 Agent Team Suite: 4–7 days
Phase 1.75 Benchmark Hardening: 4–6 days
Phase 2 Polished Public Demo: 6–10 days
```

Total: approximately 31–46 person-days.

Credible local developer benchmark adds Phase 3: +6–10 days.

Richer product mode with fictional roster budget adds Phase 4: +5–8 days.

Scouting and hidden-edge layer adds Phase 5: +7–12 days.

Hosted public arena adds Phase 6: +15–30+ days.

## 16. Final success test

The P0/P1 demo is successful only if an engine-generated seeded replay shows an agent changing strategy because of observed opponent behavior, graph-backed tactical events, resource-constrained legal choices, and Film Room feedback that gives the player a clear next adjustment.

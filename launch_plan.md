# CoachBench Launch Plan - Assistant-Led P0 / P1 / P2

Purpose: get from "honest starter repo" to a defensible LinkedIn post and a real product loop where users can build, run, watch film, adjust, and rematch without thinking in implementation tiers.

Audiences to serve:

- Football fans - must see a coordinator agent learn, adjust, and rematch in motion.
- AI/ML practitioners - must see a graph-grounded, reproducible benchmark contract they can inspect and fork.

Launch product thesis:

```text
Conversation
  -> structured policy proposal
  -> legal-action validation
  -> deterministic engine run
  -> Arena gauntlet / matchup report
  -> replay + Film Room
  -> conversation-guided adjustment
  -> rematch / rerun
```

The LLM is the interface and policy compiler. The strategy graph, legal action enumerator, resource validator, resolution engine, replay contract, Arena reports, and Film Room evidence remain the source of tactical truth.

Non-goal: shipping every `PLAN.md` phase before posting. Only items that move launch credibility, product clarity, and retention are listed here.

---

## Product Decisions

These are locked for this launch plan.

1. Users do not see Tier 0 / Tier 1 / Tier 2 at launch.
2. Tier 0 and Tier 1 become one user-facing surface: **CoachBench Assistant**.
3. Tier 2 remains implemented/documented as a developer surface but hidden from launch UI.
4. CoachBench hosts LLM usage with a CoachBench-owned API key for launch. BYO-key is not the default launch path because fan conversion would drop hard.
5. Hosted LLM usage requires hard server-side cost controls:
   - max LLM calls per user session,
   - max LLM calls per IP/time window,
   - max concurrent sessions,
   - global kill switch,
   - no model API key exposed to the browser.
6. A launch cost ceiling must be set before P0-6 implementation starts: a viral spike of 10,000 sessions/day must cost less than `LLM_VIRAL_SPIKE_COST_CEILING_USD`.
7. The Assistant can ask clarifying questions, propose policy changes, and explain Film Room evidence.
8. The Assistant must output structured policy changes that CoachBench validates before any run.
9. The Assistant must not invent tactical truth, hidden facts, graph cards, legal actions, identities, or outcomes.
10. P0 requires a local backend. The current static-only UI cannot execute Python engine runs, persist drafts honestly, orchestrate batches, or call an LLM API securely.

---

## Locked P0 Critical Path

P0 items are not parallel. Build in this order:

1. **P0-1 Local Backend, Cost Controls, And Draft Persistence**
2. **P0-2 User-Facing Arena**
3. **P0-3 Fictional Identity Layer**
4. **P0-4 Unified CoachBench App Shell**
5. **P0-5 CoachBench Assistant Policy Loop**
6. **P0-6 Graph-Grounded Hosted LLM Guardrails**
7. **P0-7 Conversational Film Room Loop**
8. **P0-8 Benchmark Story And Curated Seeds**
9. **P0-9 LinkedIn Asset And README Rewrite**

If an upstream item slips, downstream launch work should pause rather than paper over the gap.

---

## P0 - Must Land Before The LinkedIn Post

### P0-1. Local Backend, Cost Controls, And Draft Persistence

**What:** Establish the local backend foundation for Assistant calls, real engine runs, saved drafts, past matchups, and Arena jobs.

**Why:** The launch product can no longer be static-only. A conversational product with real runs, persisted drafts, and batch reports needs a backend boundary.

**Definition of done:**

- Local backend can run a fresh engine drive from a structured policy config.
- Saved Garage/Assistant drafts are persisted in SQLite via the local backend.
- Browser `localStorage` may cache UI state, but it is not the source of truth for launch drafts.
- Drafts are named, versioned, listed, and can be selected as offensive or defensive coordinators.
- Session records capture accepted policy config, opponent, seed set, report path, and replay paths.
- Server-side LLM budget controls exist even before live LLM calls are enabled.
- Server-side hard caps include session cap, IP/window cap, global cap, and kill switch.
- Cost gate is explicit: `LLM_VIRAL_SPIKE_COST_CEILING_USD` must be set before P0-6.
- No model API key is ever sent to browser code.
- Same seed + same config produces same replay.

**Surfaces:** local backend route/module, `arena/storage/`, `engine/coachbench/engine.py`, `arena/tiers/declarative.py`, `arena/tiers/prompt_policy.py`, tests.

---

### P0-2. User-Facing Arena

**What:** Promote the retention loop from one-off drives to a user-facing Arena surface.

Core capabilities:

```text
pick a saved draft as OC or DC
Best-of-N vs launch baseline opponents
local seed gauntlet with reproducible report
tournament runner across multiple saved drafts
replay export + Film Room links per match
```

**Why:** Without Arena, the Assistant loop ends after one drive. The product loop is build -> run a gauntlet -> study Film Room -> adjust -> rerun.

**Definition of done:**

- User can choose a saved draft as offense or defense.
- User can run Best-of-N against the launch baseline opponents.
- User can run a local seed gauntlet and receive an aggregate report.
- User can run a tournament across multiple saved drafts.
- Batch runs have job status, progress, completion, and failure states.
- Reports include stable local URLs for aggregate report, each replay, and each Film Room panel.
- Past matchups in the left rail are populated from persisted Arena sessions.
- Existing `arena/api/routes_challenges.py`, `arena/api/routes_jobs.py`, `arena/api/routes_leaderboard.py`, and worker code are audited before new code is written.
- If existing arena routes are at least 70% reusable, promote and relabel them for the user-facing Arena instead of rebuilding.
- If existing arena routes stay developer-only, the plan must document why before fresh implementation starts.
- Launch UI shows fictional identities by default; benchmark labels remain available in technical details.

**Surfaces:** `arena/api/routes_challenges.py`, `arena/api/routes_jobs.py`, `arena/api/routes_leaderboard.py`, `arena/worker/`, `scripts/run_best_of_n.py`, `scripts/run_gauntlet.py`, `scripts/run_tournament.py`, UI report surface, tests.

---

### P0-3. Fictional Identity Layer

**What:** Replace launch-facing Team A / Team B labels with fictional opponents and coordinator identities that have enough substance for the Assistant and Arena to reference.

**Why:** The football-fan path needs stakes and memory. Identities cannot be pure cosmetics if the Assistant will talk about them.

**Definition of done:**

- Two to four fictional launch identities exist.
- Each identity includes:
  - display name,
  - side eligibility,
  - coach/coordinator style,
  - default policy/archetype mapping,
  - preferred concept families,
  - known vulnerability/counter metadata,
  - short launch-safe bio.
- Identities map to existing graph concepts and policy defaults; they do not invent new tactical rules.
- If an identity needs new tactical behavior, that behavior must be added through graph/engine changes, not prose.
- Assistant can reference identity metadata, but only as structured context.
- Launch UI uses fictional identity by default; benchmark labels appear in technical/debug contexts.
- No AGENTS.md-prohibited identity, league, monetization, or contest language.

**Surfaces:** new identity data file, `agent_garage/profiles.json`, `ui/showcase_manifest.json`, `ui/app.js`, `README.md`, tests.

---

### P0-4. Unified CoachBench App Shell

**What:** Replace the separated Garage / Replay / Film Room feel with a single app frame.

Target layout:

```text
Left rail:
  CoachBench nav
  available opponents / games
  past matchups / recent runs

Center:
  CoachBench Assistant conversation
  prompt box
  suggested prompt empty states
  policy proposal cards
  confirmation chips / permission-style controls

Right drawer / side panel:
  Watch Film card
  field
  timeline
  Film Room
  graph evidence
  before / after
```

**Why:** The current product splits diagnosis and configuration across pages. Users should not have to remember a Film Room note while tuning elsewhere.

**Definition of done:**

- Primary nav moves to a left rail.
- Recent matchups, available games, and saved drafts appear below the left nav.
- Garage, Arena, and Film Room are accessible in one screen.
- Replay detail opens in a side panel or drawer from an "Open / Watch Film" card.
- Existing replay detail components are reused where possible instead of rebuilt.
- Tier 2 is removed from visible launch UI.
- No visible Tier 0 / Tier 1 / Tier 2 selector remains in the main app.
- Empty state includes suggested prompts, such as:
  - "Build an offense that punishes pressure without throwing picks."
  - "Make my defense disguise more without burning the rush budget."
  - "We got baited by simulated pressure. What should I change?"
  - "Build a run-first coordinator that unlocks play-action."
  - "Give me a safe red-zone defense that prevents explosives."

**Surfaces:** `ui/*.html`, `ui/app.js`, `ui/styles.css`, `ui/topbar.js`, `ui/router.js`.

---

### P0-5. CoachBench Assistant Policy Loop

**What:** Merge the current Tier 0 knobs and Tier 1 prompt-policy concept into one assistant-led policy builder.

User examples:

```text
I want an offense that punishes pressure but does not throw picks.

Make my defense disguise more, but stop burning all the rush budget.

We got baited by simulated pressure. What should I change?
```

The Assistant responds with structured proposals, not freeform tactical truth:

```json
{
  "summary": "Shift toward pressure answers without raising turnover risk.",
  "proposed_changes": [
    {
      "parameter": "screen_trigger_confidence",
      "from": 0.45,
      "to": 0.68,
      "reason": "Film Room showed pressure looks on plays 3 and 4."
    }
  ],
  "requires_confirmation": true
}
```

**Why:** Raw knobs are too arbitrary as the main product. Conversation is the natural interface, but it must compile down to inspectable policy.

**Definition of done:**

- User can describe a desired coordinator style in plain language.
- Empty state suggested prompts are clickable and produce Assistant draft proposals.
- Assistant proposes changes to the same live policy/config fields the engine can run.
- Proposal cards appear above the prompt box, similar to permission prompts.
- Each proposal has accept / reject / edit controls.
- Accepted proposals update the structured policy config.
- The structured config remains visible in a compact inspectable panel.
- The Assistant can create, update, name, and save drafts.
- The Assistant cannot directly write replay outcomes, graph cards, hidden state, legal action sets, or identity facts.
- Tests verify Assistant proposals are schema-valid and rejected if they reference unknown parameters, illegal concepts, hidden fields, or unsupported identity claims.

**Surfaces:** new assistant module, `ui/app.js`, `ui/styles.css`, `agent_garage/profiles.json`, `agent_garage/parameter_glossary.json`, `arena/tiers/prompt_policy.py`, tests.

---

### P0-6. Graph-Grounded Hosted LLM Guardrails

**What:** Connect the Assistant to an LLM API using CoachBench-hosted credentials and constrained, graph-grounded context.

Initial context should be deterministic retrieval, not overbuilt vector RAG:

```text
current policy config
current legal concept vocabulary
selected identity metadata
current replay / report summary
Film Room events
referenced graph cards
graph-listed counters
resource budget state
allowed output schema
session budget state
```

**Why:** The LLM should help users express intent and understand evidence. It should not become the simulator, and launch cannot be exposed to unbounded API spend.

**Definition of done:**

- LLM calls are made only from the backend with CoachBench-hosted credentials.
- LLM calls receive only sanitized context.
- Prompt/context includes graph-card evidence and legal vocabulary needed for the current task.
- LLM output is parsed as structured JSON.
- Invalid JSON, unknown fields, illegal concepts, hidden-field references, or unsupported claims are rejected.
- Product falls back gracefully if the LLM call fails or budget cap is reached.
- Per-session, per-IP, concurrent-session, and global call caps are enforced server-side.
- Kill switch can disable live LLM calls without breaking engine runs.
- No raw seeds, hidden traits, debug fields, endpoint secrets, or engine internals are sent to the model.
- No LLM text is treated as tactical truth unless it maps back to graph/event/identity evidence.
- Assistant produces stable, sensible proposals for 5 canonical fan prompts across 3 retries each.

Canonical fan prompts:

```text
Build an offense that punishes pressure without throwing picks.
Make my defense disguise more without burning the rush budget.
We got baited by simulated pressure. What should I change?
Build a run-first coordinator that unlocks play-action.
Give me a safe red-zone defense that prevents explosives.
```

**Surfaces:** new assistant backend adapter, cost-control module, `engine/coachbench/contracts.py`, `engine/coachbench/film_room.py`, `arena/tiers/sanitized_observation.py`, docs, tests.

---

### P0-7. Conversational Film Room Loop

**What:** Film Room becomes both a replay/report explanation and the next Assistant prompt context.

Target shape:

```text
Headline:
You attacked Bear Front with outside zone. The offense adjusted to
play-action, then took underneath space when the defense bracketed.

Evidence:
Play 1: outside_zone vs bear_front
Graph card: redzone.outside_zone_vs_bear.v1

Suggested adjustment:
Increase adaptation speed or shift earlier to quick game / play-action.
```

**Why:** Current Film Room evidence is structurally correct but too log-like. Users need a story, then proof, then a fast path to rerun.

**Definition of done:**

- Film Room headline is generated only from actual replay events and graph cards.
- Headline references observed concepts, observed counters, and outcome where available.
- No clear event means no forced headline; fallback remains structured evidence.
- Headline length capped to avoid layout shift.
- "Apply Suggested Tweak" opens an Assistant proposal, not a disconnected Garage page.
- Arena report pages link each match to its replay and Film Room panel.
- Assistant can answer "what should I change?" using the selected replay/report as context.
- Unit tests confirm headlines and Assistant context cite events that actually occurred.

**Surfaces:** `engine/coachbench/film_room.py`, `ui/app.js`, Arena report UI, tests.

---

### P0-8. Benchmark Story And Curated Seeds

**What:** Replace the fragile single-seed matrix story with aggregate evidence and curated story seeds.

**Why:** Current single-seed evidence does not robustly support "adaptation matters." Launch can survive honest limits; it cannot survive an overclaim.

**Definition of done - aggregate:**

- `scripts/run_match_matrix.py` runs at least 15 seeds per matchup cell.
- Report includes mean points per drive, success rate, EV delta, adaptation latency, counter success rate, and play-distribution shift.
- Report makes clear whether adaptive policies outperform, fail, or only win in specific matchup classes.
- If the aggregate does not show a credible adaptation signal, stop and fix engine/agents before posting.

**Definition of done - curated seeds:**

- 3-5 curated seeds are selected from the aggregate.
- Seeds demonstrate:
  - adaptation working,
  - counter-adaptation working,
  - one honest failure where adaptation does not help.
- Curated seeds appear in the left rail, Arena, home/gallery, and LinkedIn recording path.
- README references aggregate evidence for credibility and curated seeds for narrative.

**Surfaces:** `scripts/run_match_matrix.py`, `data/match_matrix_report.json`, `ui/showcase_replays/`, `ui/showcase_manifest.json`, `README.md`.

---

### P0-9. LinkedIn Asset And README Rewrite

**What:** Package the new loop into a 45-75 second recording and rewrite README above the fold.

Recording beats:

```text
pick opponent
ask Assistant for coordinator style
accept policy proposal
run gauntlet or Best-of-N
open Watch Film
apply Film Room suggestion
rerun / before-after delta
```

**Definition of done:**

- One MP4 between 45 and 75 seconds, captured at 1080p or higher.
- One 20-30 second GIF derived from the same footage, embedded in `README.md`.
- One static screenshot embedded in `README.md`.
- README opens with:
  - football-fan pitch,
  - practitioner pitch,
  - GIF,
  - quick start below the pitch.
- No placeholder screenshot text remains.
- No AGENTS.md-prohibited references visible in assets.
- No Tier 2 / endpoint / sandbox UI visible in launch asset.
- After the full launch plan is implemented and verified, delete `launch_plan.md` from the repo so the repo does not carry stale launch-planning scaffolding.

**Surfaces:** `README.md`, `docs/assets/`, launch MP4 outside repo, `launch_plan.md`.

---

## Posting Gate

Do not post until all of these are true:

1. Cost ceiling is filled in and accepted: 10,000 sessions/day costs less than `LLM_VIRAL_SPIKE_COST_CEILING_USD`.
2. LLM call caps and kill switch are enforced server-side.
3. Saved drafts persist through the local backend and can be selected as OC/DC.
4. Arena can run Best-of-N, gauntlet, and tournament jobs from saved drafts.
5. Arena reports expose stable replay and Film Room links per match.
6. CoachBench Assistant can convert natural language into structured policy proposals.
7. Assistant proposals are validated before they update config.
8. Assistant produces stable, sensible proposals for 5 canonical fan prompts across 3 retries each.
9. Accepted config runs through the real engine and produces a fresh replay.
10. Film Room opens inside the same app frame and can feed an Assistant adjustment.
11. Tuning via Assistant produces a measurable replay/report change across a fixed seed or seed pack.
12. Aggregate matrix shows a credible adaptation or counter-adaptation story.
13. LinkedIn recording shows real behavior, not nearest pre-baked replay resolution.
14. README explains the fan loop and practitioner contract without tier confusion.
15. Tier 2 UI is hidden.
16. No AGENTS.md-prohibited identity, league, monetization, or contest language appears in launch surfaces.

If any of these slip, the launch either misleads or under-sells. Both are worse than waiting.

---

## P1 - Week After Launch

These items convert post traction into product traction. Pick based on inbound signal.

### P1-1. Assistant Hardening And Evaluation

**What:** Evaluate the Assistant as a product surface, not just an API call.

**Definition of done:**

- Prompt injection attempts cannot expose hidden fields or bypass legal action validation.
- Assistant proposal rejection reasons are understandable to users.
- Common football-language asks map to stable structured policy changes.
- Repeated same prompt + same context produces stable enough proposals for launch expectations.
- LLM failure mode still lets user run a default validated policy.

---

### P1-2. Worked Arena Tune-And-Rerun Example

**What:** A concrete, reproducible example showing a Film Room note, Assistant-suggested adjustment, accepted config change, gauntlet rerun, and measurable delta.

**Definition of done:**

- New page at `docs/worked_example_tune_and_rematch.md`.
- Includes exact command or app flow to reproduce.
- Links from README.
- Uses one curated launch seed pack.

---

### P1-3. Local Developer Quickstart For Policy Authors

**What:** Preserve the practitioner path underneath the simplified product surface.

**Definition of done:**

- Docs explain that user-facing Assistant policies compile to structured local policies.
- Developer can inspect replay JSON, graph cards, Arena reports, and policy config.
- Developer can run local evaluation from CLI.
- No Tier 2 endpoint setup in the main quickstart.

---

### P1-4. Arena Scope Cleanup

**What:** Make the existing arena code clearly local-only / experimental without pretending it does not work.

**Why:** The local API and worker path exist. The problem is not fake code; the problem is launch optics and production-hosting expectations.

**Definition of done:**

- `arena/README.md` says: local-only developer surface, not production hosting.
- Main README does not route casual users into endpoint or sandbox setup.
- Security docs keep Tier 2 and Tier 3 caveats prominent.
- No "DESIGN DRAFT - NOT RUNNING" language on working local code.

---

## P2 - Only After The Assistant + Arena Loop Is Real

These items extend reach but do not fix the launch loop.

### P2-1. Tier 2 Remote Endpoint Developer Demo

**What:** Bring Tier 2 back as an advanced practitioner path with a reference endpoint and a focused quickstart.

**Definition of done:**

- Tier 2 remains hidden from main consumer UI.
- Reference endpoint is published separately.
- Local CoachBench can call the endpoint, validate response, fall back on failure, and produce replay/report.
- Docs include timeout, schema, safety, and determinism caveats.

---

### P2-2. Real Graph Retrieval Layer

**What:** Add vector or hybrid retrieval only if deterministic graph-context packing stops scaling.

**Definition of done:**

- Graph has enough cards that deterministic context selection is insufficient.
- Retrieval is tested against known replay events.
- Retrieved content is evidence only, not tactical truth.

---

### P2-3. Expand Fictional Team Narratives

**What:** Add richer fictional identities after the core loop proves useful.

**Definition of done:**

- More fictional coordinator styles and matchup hooks.
- No AGENTS.md-prohibited identity references.
- Benchmark aliases remain available for technical users.

---

### P2-4. Replace Hardcoded Film Room Tweak Rules

**What:** Replace `CARD_TWEAK_RULES` with graph-metadata-driven suggestion generation once the graph grows enough to justify it.

**Definition of done:**

- Adding a graph card can produce a sensible suggestion without editing `film_room.py`.
- Existing Film Room contract tests still pass.

---

## Intentionally Not On This Plan

- Rookie Pools and Social Share - remain backlog.
- Public hosted arena, leaderboards, and season standings - later.
- Tier 3 sandboxed code execution - separate security review required.
- Full vector RAG before deterministic graph-context packing proves insufficient.
- Launch-scope content prohibited by `AGENTS.md`.
- BYO-key as the default launch path.

If any of these are promoted, update `PLAN.md` first. Do not let them sneak into launch scope.

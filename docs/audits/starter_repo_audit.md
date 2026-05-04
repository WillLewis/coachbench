# Starter Repo Audit

## Current Phase Assessment

### Phase 0A: Spec Lock

Present:

- Product frame, non-goals, and safety boundaries are documented in `PLAN.md`, `AGENTS.md`, `CLAUDE.md`, `README.md`, and supporting docs.
- Episode, action, observation, replay, and scoring contracts are documented in `PLAN.md` section 4.
- P0 action vocabulary exists in `graph/redzone_v0/concepts.json`.
- Resource budgets and concept costs exist in `graph/redzone_v0/resource_constraints.json`.
- Graph interaction card format exists in `graph/redzone_v0/interactions.json`.
- Agent Garage, Film Room, Daily Slate, and backlog boundaries are documented.
- Graph-owned resolution and belief tuning exist in `resolution_model.json` and `belief_model.json`.

Missing or partial:

- Contract validation is lightweight Python validation, not a formal JSON Schema or versioned schema artifact.
- Some scoring concepts in `PLAN.md` remain aspirational; the starter reports points/result/play count and selected Film Room fields, but not full aggregate rates.
- The replay contract distinguishes public, side-observed, engine-internal, and debug partitions, but the debug partition is intentionally empty in P0.

### Phase 0B: Static Schema/UI Proof

Present:

- Zero-dependency replay UI exists under `ui/`.
- UI loads `ui/demo_replay.json` and supports a clickable timeline, field position, call cards, belief bars, graph events, Agent Garage profile display, Daily Slate shell text, and Film Room notes.
- Generated replay JSON is copied into the UI by `scripts/run_showcase.py --copy-ui`.
- Replay fields are backward-tolerant in `ui/app.js` for the current partitioned replay shape.

Missing or partial:

- The current replay is engine-generated, not hand-authored static proof data.
- The UI remains a starter proof, not a polished Phase 2 demo.
- Graph-card exploration is limited to event/card references shown on selected plays; there is no full graph explorer.
- UI compatibility is covered by data generation and code inspection, but there is no browser-level automated UI test.

### Phase 1 Scaffold: Engine-Generated Showcase Replay

Present:

- Legal action enumerator and restricted agent-facing facade exist in `action_legality.py`.
- Full action validation rejects malformed concepts, fields, risk levels, tags, and resource-impossible calls.
- Drive-level resource budgets reduce legal action sets as resources are spent.
- Concept interaction engine consumes graph interactions and event visibility.
- Resolution engine consumes graph-owned resolution constants.
- Observation functions split public, offense-observed, and defense-observed post-play data.
- Belief updates consume graph-owned belief deltas.
- Replay export includes public, side-observed, engine-internal, and debug partitions.
- Film Room notes are generated from structured replay events.
- Showcase, match matrix, Daily Slate, and agent validation scripts exist.
- Static and adaptive starter agents exist.

Missing or partial:

- Local agent ecosystem remains starter-level; there is no broad tournament runner or best-of-N evaluator.
- Calibration is intentionally lightweight and symbolic.
- No execution sandbox for arbitrary third-party code is implemented, which matches current safety constraints.
- Replay validation is present but not published as a standalone schema artifact.
- PLAN section 16 defines the headline P0/P1 success criterion. The seeded adaptive showcase now has a direct regression test, but it remains a starter proof rather than a broad adaptation benchmark.

## Acceptance Checklist Coverage

### Legal Action Validation

Covered by:

- `LegalActionEnumerator` and `LegalActionFacade`.
- Strict action validation in `action_legality.py`.
- Invalid-action fallback and `invalid_action_count` in `engine.py` / `replay.py`.
- Tests:
  - `test_legal_action_enumerator_rejects_invalid_action`
  - `test_validation_rejects_tampered_action_fields_and_risk`
  - `test_drive_resources_reduce_legal_action_sets`
  - `test_invalid_third_party_action_records_fallback_instead_of_crashing`

Assessment: Covered for starter scope.

### Deterministic Seed Behavior

Covered by:

- Engine-local `random.Random(seed)`.
- Hashed seed metadata instead of raw seed exposure.
- Content-addressed match matrix case seeds.
- Explicit Daily Slate seed/matchup entries.
- Tests:
  - `test_showcase_replay_is_deterministic`
  - `test_match_matrix_seed_is_content_addressed`
  - `test_daily_slate_entries_are_explicit_and_legacy_lengths_are_validated`

Assessment: Covered for same-seed local replay generation.

### Observation Safety

Covered by:

- Agent-facing legal facade does not expose graph internals.
- Pre-commit observations do not expose opponent calls, shell placeholders, seed internals, future plays, or debug data.
- Post-play observations are side-filtered by graph event visibility.
- Tests:
  - `test_agent_legal_api_does_not_expose_graph`
  - `test_pre_commit_observations_do_not_include_mock_alignment_signals`
  - `test_replay_separates_public_side_observed_and_internal_fields`
  - `test_side_observations_filter_private_event_visibility`
  - `test_observation_safety_validator_rejects_hidden_fields`

Assessment: Covered for current local agent API and replay structure.

### Replay JSON UI Compatibility

Covered by:

- `scripts/run_showcase.py --copy-ui` writes `ui/demo_replay.json`.
- `ui/app.js` consumes the current partitioned replay shape.
- `validate_replay_contract` checks required replay partitions and fields.
- Required generation command succeeds.

Assessment: Covered at data-contract level. Browser-level UI rendering is not automated.

### Film Room Event Derivation

Covered by:

- `film_room.py` derives notes from observed replay event tags.
- `validate_film_room_is_event_derived` rejects unsupported notes.
- Tests:
  - `test_film_room_notes_must_be_event_derived`
  - `test_film_room_notes_must_reference_observed_card_ids`
  - graph event visibility tests in `test_graph_invariants.py`

Assessment: Covered for existing Film Room note vocabulary and observed graph-card references.

### PLAN §16 Final Success Test

Covered by:

- The seed-42 adaptive showcase contains an end-to-end adaptation loop:
  - offense changes from outside zone into play action after observed defensive front events
  - defense changes into bracket coverage after observed run-tendency events
  - tactical events reference graph card IDs
  - selected actions are legal within each play's resource-constrained legal set
  - Film Room emits graph-card-derived notes and counter-oriented tweaks
- Test:
  - `test_plan_final_success_seeded_demo_shows_adaptation_loop`

Assessment: Covered as a starter seeded-demo regression. Still not a statistical or multi-seed adaptation benchmark.

### Daily Slate Reproducibility

Covered by:

- `data/daily_slate/sample_slate.json` uses explicit seed/matchup entries.
- `run_daily_slate.py` rejects mismatched legacy seed/matchup arrays.
- `validate_daily_slate_report` checks report shape.
- Tests:
  - `test_daily_slate_entries_are_explicit_and_legacy_lengths_are_validated`
  - `test_scoring_reports_satisfy_contracts`

Assessment: Covered for local fixed-entry slate reports.

### Licensed-Reference Safety

Covered by:

- Product boundary docs in `README.md`, `PLAN.md`, `AGENTS.md`, and `CLAUDE.md`.
- Graph invariant test scans graph JSON for banned terms.
- Fictional/neutral naming is used in graph, agents, and generated outputs.

Assessment: Covered for graph files. Broader repo-wide generated-output scanning is still a recommended hardening ticket.

## Test Coverage Gaps

- No browser automation test verifies that `ui/index.html` renders `ui/demo_replay.json` without runtime errors.
- Contract validation is Python-based; there is no formal JSON Schema file for external consumers.
- Film Room derivation tests cover current note vocabulary but not every possible future event tag.
- Licensed-reference safety is strongest for graph JSON; a repo-wide text scan is not yet part of `pytest`.
- Daily Slate tests validate shape and mismatched legacy arrays, but do not compare full report output against a golden fixture.
- Match matrix reproducibility is tested at seed function level, but there is no golden report diff test.
- Resource depletion is tested with targeted budget examples, not with exhaustive per-drive legal-set transitions across all actions.
- Agent Garage profile wiring is present for showcase adaptive agents, but tests do not yet assert every profile parameter has behavioral influence.
- PLAN section 16 is covered by one seeded adaptive showcase regression, not by a matrix of agents/seeds.

## Recommended Next Implementation Tickets

1. Add a formal replay JSON Schema artifact generated from or aligned with `coachbench.contracts`.
2. Add a lightweight browser/UI smoke test that serves `ui/` and verifies the replay loads without JavaScript errors.
3. Add repo-wide licensed/prohibited-reference scanning to `pytest`, covering docs, scripts, graph, data, and UI.
4. Add golden output tests for showcase replay, match matrix, and Daily Slate reports using fixed seeds.
5. Expand Film Room tests so every supported graph event tag is either mapped to a note/tweak or intentionally ignored.
6. Add exhaustive action-validation tests for each offense and defense action field against graph-declared action fields.
7. Add resource-transition tests across a multi-play drive to prove legal action sets shrink predictably after each resource spend.
8. Add Agent Garage profile contract tests that verify visible config values compile into legal policy parameters without bypassing the legal action facade.

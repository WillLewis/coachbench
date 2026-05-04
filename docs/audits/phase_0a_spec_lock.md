# Phase 0A Spec Lock

Phase 0A is locked. Changes to the artifacts below require a follow-up audit entry.

## Deliverables

| # | Deliverable | Locked artifact paths | Asserting test |
|---|---|---|---|
| 1 | benchmark contract | `PLAN.md` section 4, `docs/product_plan.md` section 4 | `test_generated_replay_satisfies_replay_contract` |
| 2 | episode schema | `PLAN.md` section 4.1, `docs/episode_example.md`, `engine/coachbench/contracts.py` | `test_episode_example_documents_plan_4_1_fields` |
| 3 | action schema | `PLAN.md` section 4.2, `engine/coachbench/schema.py`, `engine/coachbench/contracts.py` | `test_action_schema_validator_requires_contract_fields` |
| 4 | observation schema | `PLAN.md` section 4.3, `engine/coachbench/observations.py`, `engine/coachbench/contracts.py` | `test_observation_builders_only_return_allowlisted_fields` |
| 5 | replay schema | `PLAN.md` section 4.4, `engine/coachbench/replay.py`, `engine/coachbench/contracts.py` | `test_validate_replay_contract_rejects_missing_top_level_partition` |
| 6 | scoring schema | `PLAN.md` section 4.5, `engine/coachbench/contracts.py`, `scripts/run_match_matrix.py`, `scripts/run_daily_slate.py` | `test_scoring_reports_satisfy_contracts` |
| 7 | P0 action vocabulary | `PLAN.md` section 8, `graph/redzone_v0/concepts.json` | `test_all_interaction_references_exist_in_concept_vocabularies` |
| 8 | resource-budget rules | `graph/redzone_v0/resource_constraints.json`, `tests/fixtures/legal_action_sets_full_budget.json` | `test_legal_action_enumerator_matches_full_budget_snapshot` |
| 9 | graph-card format | `graph/redzone_v0/interactions.json`, `graph/redzone_v0/graph_tests.json` | `test_every_interaction_declares_counters_and_limitations` |
| 10 | product non-goals | `PLAN.md` section 3, `docs/backlog.md` | `test_p0_scope_terms_stay_inside_allowed_boundary_docs` |
| 11 | license-safe naming rules | `AGENTS.md`, `CLAUDE.md`, `README.md`, `graph/redzone_v0/graph.meta.json` | `test_repo_contains_no_banned_licensed_or_monetized_terms` |
| 12 | Agent Garage v0 spec | `PLAN.md` section 5.2, `docs/agent_garage.md`, `agent_garage/profiles.json` | `test_agent_garage_doc_lists_plan_5_2_controls` |
| 13 | Film Room v0 spec | `PLAN.md` section 6, `docs/film_room.md`, `engine/coachbench/film_room.py` | `test_film_room_notes_must_reference_observed_card_ids` |
| 14 | Daily Slate v0 spec | `PLAN.md` section 7.2, `docs/daily_slate.md`, `data/daily_slate/sample_slate.json` | `test_daily_slate_script_output_is_deterministic_and_contract_valid` |
| 15 | Backlog section | `PLAN.md` section 14, `docs/backlog.md` | `test_p0_scope_terms_stay_inside_allowed_boundary_docs` |

## Exit Criteria

| Exit | Criterion | Status | Asserting test |
|---|---|---|---|
| E1 | everyone can describe one episode | PASS | `test_episode_example_documents_plan_4_1_fields` |
| E2 | everyone knows what agents can and cannot see | PASS | `test_observation_builders_only_return_allowlisted_fields` |
| E3 | everyone knows what actions are legal | PASS | `test_legal_action_enumerator_matches_full_budget_snapshot` |
| E4 | everyone knows what replay JSON must contain | PASS | `test_validate_replay_contract_rejects_missing_top_level_partition` |
| E5 | P0 scope is bounded | PASS | `test_p0_scope_terms_stay_inside_allowed_boundary_docs` |

## Gap Closure

| Gap | Status | Evidence |
|---|---|---|
| G1 | PASS | `docs/agent_garage.md` includes `resource conservation`. |
| G2 | PASS | `test_repo_contains_no_banned_licensed_or_monetized_terms` scans `docs/`, `scripts/`, `ui/`, `data/`, `agents/`, and `engine/`. |
| G3 | PASS | `docs/episode_example.md` gives concrete fictional values for each PLAN section 4.1 field. |
| G4 | PASS | `OBSERVATION_ALLOWED_FIELDS` and `test_observation_builders_only_return_allowlisted_fields` enforce observation allow-lists. |
| G5 | PASS | `tests/fixtures/legal_action_sets_full_budget.json` and `test_legal_action_enumerator_matches_full_budget_snapshot` lock full-budget legal sets. |
| G6 | PASS | `test_validate_replay_contract_rejects_missing_top_level_partition` and `test_validate_replay_contract_rejects_nonempty_debug_partition` cover replay partition failures. |
| G7 | PASS | `test_p0_scope_terms_stay_inside_allowed_boundary_docs` bounds P0 scope terms to explicit boundary docs. |
| G8 | PASS | This document lists the deliverables and PASS criteria. |

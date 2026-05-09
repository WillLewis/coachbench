# P0-7 Film Room Audit

## Narrative Algorithm

`engine/coachbench/film_room.py:narrative_for_drive()` is deterministic and length-capped at `NARRATIVE_MAX_CHARS = 200`. It builds candidates only from `_public_play(play)` and `_observed_events(play)`. The primary card is the observed graph card with largest absolute public expected-value delta, tie-broken by smallest play index and card id. The story uses `card_label()` and `concept_label()` for the primary card, observed offensive concept, and observed defensive coverage. A second adjustment sentence is included only when a later observed card/concept exists in the adaptation chain or event candidates. Terminal outcome comes from the final public play, including public `next_state.points` when available.

`narrative_for_drive()` returns `None` when there are no observed graph-card events, when the Film Room only has `NO_EVENT_FILM_ROOM_NOTE`, or when the sentence cannot fit the cap cleanly. It never emits numeric internals, seeds, hidden fields, debug fields, tier vocabulary, real-world sports references, or restricted monetization language.

## Replay / Context Fields

Replay JSON adds one field only: `film_room.narrative: str | null`, inserted after the existing `headline`. The existing `headline` remains the short terminal label for backward compatibility.

`arena/llm/context.py:pack_context()` adds top-level `film_room_narrative: str | null`. It is top-level because the narrative is a drive-level summary, not a per-play field. `SAFE_REPLAY_PLAY_FIELDS` is unchanged; per-play summaries remain constrained to the P0-6 safe field set.

## Reports Route

The Reports route now uses `GET /v1/arena/reports?limit=20`, a lightweight metadata endpoint over existing job/progress storage. It lists report rows by job id, kind, created/completed time, status, completed/total runs, failed runs, and `has_report`. Clicking a row loads the canonical report from `GET /v1/arena/jobs/{job_id}/report`. Each match renders identity labels, seed, winner/points, `Watch Film`, and `Discuss with Assistant`. `Watch Film` uses the existing replay drawer path; `Discuss with Assistant` dispatches the existing `film_room_tweak` event.

## Fixtures / Baseline

Pre-P0-7 `data/demo_replay.json` sha256: `93c05c662de4cc17cd1be5885f4d30465249649c2198d32cab00a8e7d160a745`.

Post-P0-7 `data/demo_replay.json` sha256: `7d34e06e7a97ef77c83a2c686281ba99e0f50f544ca07993cdf2d0015004f7c8`.

Regenerated fixtures: `data/demo_replay.json`, `ui/demo_replay.json`, `ui/showcase_replays/seed_{42,99,202,311,404,515,628,733,841,956,1063,1170}.json`, `data/golden_replays/{42,99,202,311,404}.json`, `data/match_matrix_report.json`, `data/daily_slate/results.json`, and `data/daily_slate/replays/daily-slate-local-v0_{42,99,202}.json`.

## Test / Safety Notes

`tests/test_film_room_tweaks.py` and `tests/test_film_room_cleanup.py` are untouched. `arena/llm/context.py:SAFE_REPLAY_PLAY_FIELDS` is unchanged. `ui/index.html` and `ui/home.js` have zero diff.

Manual smoke commands:

```bash
python -m uvicorn arena.api.app:app --host 127.0.0.1 --port 8766
# open ui/app.html, click a past matchup, confirm Drive Story appears
# navigate #/reports, expand a report, use Watch Film and Discuss with Assistant
```

# Model Smoke Findings — Live Anthropic Run
**Date:** 2026-05-12
**Model:** claude-sonnet-4-6 (provider default)
**Candidate:** `agents.model_offense.ModelOffense`
**Baseline:** `agents.static_offense.StaticOffense`
**Seed pack:** smoke (5 seeds: 6, 10, 42, 72, 99)
**Reports compared:**
- `data/eval/reports/model_smoke.json` (ModelOffense candidate)
- `data/eval/reports/smoke.json` (AdaptiveOffense candidate — deterministic baseline for context)

## TL;DR

- The live model path produced a report, but `fallback_rate_candidate` was `1.0`: every observable ModelOffense candidate turn fell back through validation (`21/21` candidate plays).
- ModelOffense did not beat the deterministic AdaptiveOffense context run: both posted `1.4` points per drive, `0.2` touchdown rate, `0.0` mean lift, and `0.0` paired-seed win rate.
- Strategy diversity was materially worse for ModelOffense: one concept at `1.0` frequency and `0.0` entropy, versus three adaptive concepts and `1.5677` entropy.
- Both runs had `lift_strength: none` and `bootstrap_ci_95: [0.0, 0.0]`; the main finding is contract failure, not lift signal.

## Contract Health

`fallback_rate_candidate` was `1.0`. The report does not include raw provider responses, so it cannot distinguish malformed JSON from missing `concept_family` or illegal concept selection. It does show that the validator fallback fired on every ModelOffense candidate play:

| Seed | Candidate plays | Offense validation failures |
|---|---:|---:|
| 6 | 4 | 4 |
| 10 | 3 | 3 |
| 42 | 4 | 4 |
| 72 | 6 | 6 |
| 99 | 4 | 4 |

That implies the live model output was not usable as direct tactical input in this smoke. The engine still completed by applying fallback behavior, which protected legality but removed most model-agent signal.

## Performance vs Deterministic Adaptive Baseline

| Metric | Model | Adaptive | Δ |
|---|---:|---:|---:|
| points_per_drive_candidate | 1.4 | 1.4 | 0.0 |
| touchdown_rate_candidate | 0.2 | 0.2 | 0.0 |
| paired_seed_lift_mean | 0.0 | 0.0 | 0.0 |
| paired_seed_win_rate | 0.0 | 0.0 | 0.0 |
| bootstrap_ci_95 | [0.0, 0.0] | [0.0, 0.0] | (0.0, 0.0) |
| lift_strength | none | none | — |

The table shows performance parity, not model advantage. Because the model fallback rate was `1.0`, the equal points, touchdown rate, lift, and confidence interval should be read as fallback-protected smoke completion rather than evidence that the model agent is competitive with the deterministic adaptive agent.

## Strategy Diversity

| Aspect | Model | Adaptive |
|---|---|---|
| concept_frequency_candidate | {"screen": 1.0} | {"bunch_mesh": 0.2962962962962963, "outside_zone": 0.2962962962962963, "rpo_glance": 0.4074074074074074} |
| Top-1 concept | screen:1.0 | rpo_glance:0.4074074074074074 |
| Distinct concepts | 1 | 3 |
| concept_entropy_candidate | 0.0 | 1.5677 |

**Concepts called only by model:** `screen`
**Concepts called only by adaptive:** `bunch_mesh`, `outside_zone`, `rpo_glance`
**Shared concepts:** none

ModelOffense explored a narrower concept space than AdaptiveOffense in this smoke. The model run collapsed to `screen` at `1.0` frequency, while the adaptive run spread calls across three concepts with top-1 frequency `0.4074074074074074` and entropy `1.5677`.

## Per-Seed Breakdown

| Seed | Model lift | Adaptive lift | Direction match? |
|---|---:|---:|---|
| 6 | 0 | 0 | yes |
| 10 | 0 | 0 | yes |
| 42 | 0 | 0 | yes |
| 72 | 0 | 0 | yes |
| 99 | 0 | 0 | yes |

The two agents agreed directionally on all five seeds because both had zero lift on every seed. There were no opposite-direction seeds where one candidate beat StaticOffense and the other lost to it.

## Gates

**Model run:**
- lift_strength: none
- failed: `fallback_rate_candidate=1.0 > 0.0`; `fallback_rate_candidate=1.0 > 0.0 (opponent=static_defense_baseline)`
- warnings: `concept_top1=1.0 > 0.4 (screen, candidate, opponent=static_defense_baseline)`; `concept_entropy_candidate=0.0 < 1.5 (candidate, opponent=static_defense_baseline)`

**Adaptive run:**
- lift_strength: none
- failed: none
- warnings: `concept_top1=0.4074 > 0.4 (rpo_glance, candidate, opponent=static_defense_baseline)`

## Surprises and Risks

- The live model path did not simply underperform; it failed the action contract on every candidate turn observed in the report.
- The `screen:1.0` concept frequency is fallback-shaped and should not be interpreted as intentional model strategy.
- Performance parity with AdaptiveOffense is not meaningful while `fallback_rate_candidate` is `1.0`.
- The smoke did confirm that the engine can contain invalid live model outputs and still emit a complete report with `errors: []`; the adaptive context run only has a mild top-1 concentration warning.

## Recommended Next Step

B. Tighten prompt before another live run. The blocking issue is `fallback_rate_candidate=1.0`, which means a delta-tool comparison would mostly compare fallback behavior rather than live model strategy. Fix the response contract first, then rerun only the smoke before spending on broader comparisons.

## Raw Report Hashes

- model_smoke.json: `a2a92b8aa881ba50aabe39491f80a80818d7113e857c804ab6c3b56274e9cbc8`
- smoke.json: `0b86148654e6b22303b0da7458c94adc2dc81f85fac25cd7e40774b488f73d41`

These hashes anchor the findings to specific report files. If either report is regenerated, the findings should be regenerated.

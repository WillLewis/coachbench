# Calibration Notes

P0 calibration is intentionally lightweight. The starter uses symbolic expected-value and success modifiers. Do not claim predictive real-world accuracy.

P0 sanity goals:

```text
red-zone outcomes should feel plausible
resource-heavy calls should have costs
strong tactics should have counters
seeded results should be reproducible
agent differences should be visible across multiple seeds
```

Future calibration may use publicly permissible aggregate rates, but tactical truth should remain graph-backed and limitations should be documented.

The Phase 1.75 sanity ranges in `sanity_ranges.json` bracket the current adaptive-vs-adaptive 20-seed behavior: 4.2 mean points per drive, 0.60 touchdown rate, 0.0 field-goal and turnover rates, 5.5 mean plays per drive, and zero invalid actions. The ranges are intentionally broad except for invalid actions, where any nonzero value means a well-formed starter agent emitted an illegal call.

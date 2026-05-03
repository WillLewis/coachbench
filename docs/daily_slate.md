# Daily Slate

Daily Slate is a fixed-seed local challenge set. It gives players a repeatable reason to return without introducing wagering or hosted execution.

## P0 local version

```text
explicit seed/matchup entries
fictional team context
baseline/adaptive matchups
engine-generated replays
Film Room output per seed
summary report
```

Slate files should prefer:

```json
{
  "entries": [
    {"seed": 42, "matchup": {"offense": "adaptive", "defense": "static"}}
  ]
}
```

Legacy `seeds` and `matchups` arrays are accepted only when their lengths match exactly.

Run:

```bash
python scripts/run_daily_slate.py --slate data/daily_slate/sample_slate.json --out data/daily_slate/results.json
```

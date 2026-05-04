# Episode Example

This worked example gives concrete fictional values for every PLAN section 4.1 episode field.

```json
{
  "episode_id": "showcase-73475cb40a56",
  "graph_version": "0.1.0",
  "engine_version": "0.1.0",
  "seed": 42,
  "seed_hash": "73475cb40a56",
  "start_yardline": 22,
  "max_plays": 8,
  "down": 1,
  "distance": 10,
  "score_mode": "red_zone_points",
  "drive_terminal_condition": "touchdown"
}
```

P0 replay metadata stores `seed_hash` instead of the raw seed. The raw seed is local runner input only and is not exposed in replay metadata.

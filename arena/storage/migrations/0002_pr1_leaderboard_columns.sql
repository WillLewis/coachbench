PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE leaderboard_seasons_new (
    season_id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    seed_set_hash TEXT NOT NULL,
    max_plays INTEGER NOT NULL,
    opponent_kind TEXT NOT NULL,
    league TEXT NOT NULL DEFAULT 'sandbox',
    created_at TEXT NOT NULL,
    closed_at TEXT,
    CHECK(league IN ('rookie','policy','endpoint',
                     'sandbox','research'))
);
INSERT INTO leaderboard_seasons_new
SELECT season_id, label, seed_set_hash, max_plays,
       opponent_kind, 'sandbox', created_at, closed_at
FROM leaderboard_seasons;
DROP TABLE leaderboard_seasons;
ALTER TABLE leaderboard_seasons_new RENAME TO leaderboard_seasons;
ALTER TABLE leaderboard_runs
    ADD COLUMN access_tier TEXT NOT NULL
    DEFAULT 'sandboxed_code';
COMMIT;
PRAGMA foreign_keys=ON;

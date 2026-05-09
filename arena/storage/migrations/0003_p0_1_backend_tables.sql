CREATE TABLE IF NOT EXISTS drafts (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  version INTEGER NOT NULL,
  side_eligibility TEXT NOT NULL,
  tier TEXT NOT NULL,
  config_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  CHECK(side_eligibility IN ('offense','defense','either')),
  CHECK(tier IN ('declarative','prompt_policy'))
);
CREATE INDEX IF NOT EXISTS idx_drafts_updated_at ON drafts(updated_at);

CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  offense_draft_id TEXT NOT NULL,
  defense_draft_id TEXT NOT NULL,
  opponent_label TEXT,
  seed INTEGER NOT NULL,
  seed_pack TEXT,
  report_path TEXT,
  replay_paths_json TEXT NOT NULL,
  status TEXT NOT NULL,
  CHECK(status IN ('completed','running','failed'))
);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at);

CREATE TABLE IF NOT EXISTS llm_calls (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  ip TEXT NOT NULL,
  ts TEXT NOT NULL,
  tokens_in INTEGER NOT NULL DEFAULT 0,
  tokens_out INTEGER NOT NULL DEFAULT 0,
  cost_usd_est REAL NOT NULL DEFAULT 0.0
);
CREATE INDEX IF NOT EXISTS idx_llm_calls_session ON llm_calls(session_id);
CREATE INDEX IF NOT EXISTS idx_llm_calls_ip_ts ON llm_calls(ip, ts);
CREATE INDEX IF NOT EXISTS idx_llm_calls_ts ON llm_calls(ts);

CREATE TABLE IF NOT EXISTS llm_concurrency (
  session_id TEXT PRIMARY KEY,
  started_at TEXT NOT NULL
);

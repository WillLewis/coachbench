CREATE TABLE IF NOT EXISTS arena_job_progress (
  job_id TEXT PRIMARY KEY,
  completed_runs INTEGER NOT NULL DEFAULT 0,
  total_runs INTEGER NOT NULL DEFAULT 0,
  failed_runs INTEGER NOT NULL DEFAULT 0,
  report_path TEXT,
  updated_at TEXT NOT NULL
);

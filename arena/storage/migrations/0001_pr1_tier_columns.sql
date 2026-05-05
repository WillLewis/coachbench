PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE agent_submissions_new (
    agent_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    source_hash TEXT NOT NULL,
    source_path TEXT NOT NULL,
    side TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    qualification_status TEXT NOT NULL,
    qualification_report_path TEXT,
    label TEXT NOT NULL,
    banned_reason TEXT,
    access_tier TEXT NOT NULL DEFAULT 'sandboxed_code',
    tier_config_path TEXT,
    endpoint_url_hash TEXT,
    UNIQUE(owner_id, name, version),
    CHECK(access_tier IN ('declarative', 'prompt_policy',
                          'remote_endpoint',
                          'sandboxed_code'))
);
INSERT INTO agent_submissions_new (
    agent_id, owner_id, name, version, source_hash, source_path, side,
    submitted_at, qualification_status, qualification_report_path,
    label, banned_reason, access_tier
)
SELECT
    agent_id, owner_id, name, version, source_hash, source_path, side,
    submitted_at, qualification_status, qualification_report_path,
    label, banned_reason, 'sandboxed_code'
FROM agent_submissions;
DROP TABLE agent_submissions;
ALTER TABLE agent_submissions_new RENAME TO agent_submissions;
CREATE INDEX IF NOT EXISTS idx_status ON agent_submissions(qualification_status);
COMMIT;
PRAGMA foreign_keys=ON;

ALTER TABLE drafts ADD COLUMN identity_id TEXT;
ALTER TABLE sessions ADD COLUMN offense_label TEXT;
ALTER TABLE sessions ADD COLUMN defense_label TEXT;
ALTER TABLE sessions ADD COLUMN offense_technical_label TEXT;
ALTER TABLE sessions ADD COLUMN defense_technical_label TEXT;

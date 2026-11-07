ALTER TABLE auth_sessions ADD COLUMN device_id TEXT
    REFERENCES devices(id) ON DELETE SET NULL;

ALTER TABLE auth_sessions ADD COLUMN last_used_at TEXT;

ALTER TABLE scan_sessions ADD COLUMN deleted_at TEXT;

CREATE INDEX IF NOT EXISTS idx_auth_sessions_token_active
    ON auth_sessions(refresh_token_hash, revoked_at, expires_at);

CREATE INDEX IF NOT EXISTS idx_devices_user
    ON devices(user_id, last_seen_at DESC);

CREATE INDEX IF NOT EXISTS idx_scans_device_created
    ON scan_sessions(device_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_scans_visible_history
    ON scan_sessions(status, deleted_at, created_at DESC);

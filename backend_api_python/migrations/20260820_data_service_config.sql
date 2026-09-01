-- Local data service runtime configuration (UI-editable overrides)

CREATE TABLE IF NOT EXISTS qd_data_service_config (
    config_key VARCHAR(64) PRIMARY KEY,
    value JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

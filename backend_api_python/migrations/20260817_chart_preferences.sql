-- Persist K-line / chart display preferences (candle color scheme, etc.).
ALTER TABLE qd_users
    ADD COLUMN IF NOT EXISTS chart_preferences TEXT DEFAULT '';

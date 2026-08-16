-- =============================================================================
-- Market data maintenance: persistent bars/ticks + maint runs + watchlist
-- =============================================================================
CREATE TABLE IF NOT EXISTS qd_market_bars (
    id BIGSERIAL PRIMARY KEY,
    market VARCHAR(32) NOT NULL,
    symbol VARCHAR(64) NOT NULL,
    timeframe VARCHAR(16) NOT NULL,
    exchange_id VARCHAR(32) NOT NULL DEFAULT '',
    market_type VARCHAR(32) NOT NULL DEFAULT '',
    bar_time BIGINT NOT NULL,
    open DOUBLE PRECISION NOT NULL,
    high DOUBLE PRECISION NOT NULL,
    low DOUBLE PRECISION NOT NULL,
    close DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION NOT NULL DEFAULT 0,
    source VARCHAR(48) NOT NULL DEFAULT '',
    quality_flags JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (market, symbol, timeframe, exchange_id, market_type, bar_time)
);
CREATE INDEX IF NOT EXISTS idx_market_bars_lookup
  ON qd_market_bars(market, symbol, timeframe, bar_time DESC);
CREATE INDEX IF NOT EXISTS idx_market_bars_exchange
  ON qd_market_bars(exchange_id, market_type, symbol, bar_time DESC);

CREATE TABLE IF NOT EXISTS qd_market_ticks (
    id BIGSERIAL PRIMARY KEY,
    market VARCHAR(32) NOT NULL DEFAULT 'Futures',
    symbol VARCHAR(64) NOT NULL,
    exchange_id VARCHAR(32) NOT NULL DEFAULT 'ctp',
    tick_time_ms BIGINT NOT NULL,
    last_price DOUBLE PRECISION NOT NULL,
    volume BIGINT NOT NULL DEFAULT 0,
    bid DOUBLE PRECISION NOT NULL DEFAULT 0,
    ask DOUBLE PRECISION NOT NULL DEFAULT 0,
    open_interest DOUBLE PRECISION NOT NULL DEFAULT 0,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_market_ticks_symbol_time
  ON qd_market_ticks(symbol, tick_time_ms DESC);
CREATE INDEX IF NOT EXISTS idx_market_ticks_created
  ON qd_market_ticks(created_at DESC);

CREATE TABLE IF NOT EXISTS qd_market_data_watch (
    id BIGSERIAL PRIMARY KEY,
    market VARCHAR(32) NOT NULL,
    symbol VARCHAR(64) NOT NULL,
    timeframe VARCHAR(16) NOT NULL DEFAULT '1m',
    exchange_id VARCHAR(32) NOT NULL DEFAULT '',
    market_type VARCHAR(32) NOT NULL DEFAULT '',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    lookback_bars INTEGER NOT NULL DEFAULT 1500,
    notes TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (market, symbol, timeframe, exchange_id, market_type)
);
CREATE INDEX IF NOT EXISTS idx_market_data_watch_enabled
  ON qd_market_data_watch(enabled) WHERE enabled = TRUE;

CREATE TABLE IF NOT EXISTS qd_market_data_maint_runs (
    id BIGSERIAL PRIMARY KEY,
    run_kind VARCHAR(24) NOT NULL DEFAULT 'historical',
    trigger_type VARCHAR(24) NOT NULL DEFAULT 'manual',
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    result JSONB NOT NULL DEFAULT '{}'::jsonb,
    CHECK (run_kind IN ('realtime', 'historical', 'retention')),
    CHECK (status IN ('running', 'success', 'partial', 'failed', 'skipped'))
);
CREATE INDEX IF NOT EXISTS idx_market_data_maint_runs_started
  ON qd_market_data_maint_runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_market_data_maint_runs_kind
  ON qd_market_data_maint_runs(run_kind, started_at DESC);

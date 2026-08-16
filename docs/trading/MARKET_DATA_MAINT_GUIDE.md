# Market Data Continuity and Accuracy Maintenance

QuantDinger can run dedicated **realtime** and **historical** maintenance jobs
that keep watched symbols continuous and numerically consistent.

## Goals

- Detect missing bars (data gaps) vs expected session breaks
- Validate OHLC/volume accuracy before persistence
- Backfill recoverable holes from upstream market-data adapters
- Persist CTP ticks (optional) and aggregate completed 1m bars
- Resubscribe stale CTP instruments automatically

## Storage

Schema (idempotent in `migrations/init.sql`):

- `qd_market_bars` — validated OHLCV bars
- `qd_market_ticks` — optional tick archive (default retention 7 days)
- `qd_market_data_watch` — watchlist
- `qd_market_data_maint_runs` — run audit

## Enable

```bash
MARKET_DATA_MAINT_ENABLED=true
MARKET_DATA_MAINT_WATCHLIST=Futures:rb2505:1m@ctp:futures
CTP_MD_ENABLED=true
CTP_MD_INSTRUMENTS=rb2505
```

`CTP_MD_INSTRUMENTS` are automatically added as Futures `1m` watch targets.

## Processes

| Mode | Owner | Behavior |
| --- | --- | --- |
| Realtime | Trading process thread | Hook CTP ticks, buffer/persist, aggregate 1m bars, resubscribe stale feeds |
| Historical | Celery Beat → maintenance queue | Fetch upstream klines, validate, upsert, attempt gap backfill |
| Retention | Celery Beat | Purge old ticks/bars by retention policy |

## API

- `GET /api/market-data-maint/status`
- `POST /api/market-data-maint/historical/run`
- `POST /api/market-data-maint/retention/run`
- `POST /api/market-data-maint/watchlist`

## Accuracy rules

Bars are rejected when:

- any OHLC price is `<= 0`
- `high < max(open, close, low)` or `low > min(open, close, high)`
- volume is negative
- duplicate timestamps appear in the same batch

Realtime tick spikes beyond `MARKET_DATA_MAINT_PRICE_SPIKE_RATIO` are counted as anomalies and logged; cumulative volume resets are treated as session boundaries.

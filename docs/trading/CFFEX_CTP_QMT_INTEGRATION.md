# CFFEX Index Futures / Options Integration

**Scope**: China Financial Futures Exchange equity-index products  
**Markets**: `CNIndexFutures` (IF/IH/IC/IM), `CNIndexOptions` (IO/HO/MO)  
**Channels**: `ctp`, `qmt`  
**Status**: Index **futures** live policy + simulation runtime are enabled. Options remain research/paper. Real CTP/QMT gateway bridges are operator-supplied.

## What landed

| Layer | Detail |
| --- | --- |
| Contract model | `app/markets/cn_index_derivatives.py` — roots, multipliers, ticks, margin rates |
| Market modules | `CNIndexFutures` (research/backtest/paper/live), `CNIndexOptions` (research/backtest/paper) |
| Compliance quotes | `app/data_sources/cffex.py` via `CFFEX_MARKET_DATA_PROVIDER=compliance\|akshare` |
| Open/close runtime | `app/services/cffex_trading/runtime.py` — margin, 今仓/昨仓, commission |
| Channels | `CtpClient` / `QmtClient` simulation by default; live needs `CFFEX_LIVE_TRADING_ENABLED=true` + external bridge |
| Policy matrix | `ctp`/`qmt` × `CNIndexFutures` × `futures` in `broker_market_policy.py` |

## Strategy config example

```json
{
  "exchange_id": "ctp",
  "market_category": "CNIndexFutures",
  "market_type": "futures",
  "trade_direction": "both",
  "bot_type": "trend",
  "symbol": "CNIndexFutures:IF2509"
}
```

Instrument prefixes: `CNIndexFutures:IF2509`, `CNIndexOptions:IO2509-C-4000`.  
Bare codes such as `IF2509` are **not** inferred as US stocks and require an explicit prefix.

## Safety boundaries

- Generic `Futures` data source **refuses** CFFEX symbols (no Binance/CME fallback).
- `CNIndexOptions` is **not** in `LIVE_MARKET_CATEGORIES`.
- Live CTP/QMT order routing is blocked unless `CFFEX_LIVE_TRADING_ENABLED=true` and a native bridge is configured (not bundled).
- Visibility defaults off: set `SHOW_CN_INDEX_DERIVATIVES=true` or include the markets in `ENABLED_MARKETS`.

## Tests

```bash
cd backend_api_python
PYTHONPATH=. pytest tests/test_cffex_ctp_qmt_integration.py tests/test_broker_market_policy.py -q
```

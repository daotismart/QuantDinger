# Mainland China Futures & Futures Options

**Exchanges**: CFFEX · SHFE · DCE · CZCE · INE · GFEX  
**Markets**: `CNFutures`, `CNFuturesOptions` (plus legacy `CNIndexFutures` / `CNIndexOptions`)  
**Channels**: `ctp`, `qmt`

## Capabilities

| Layer | Detail |
| --- | --- |
| Contract catalog | 60+ mainstream roots in `app/markets/cn_futures.py` |
| Quotes / history | `CnFuturesDataSource` — provider `auto` (akshare full history) / `akshare` / `compliance` |
| Open/close runtime | Margin, 今/昨仓, futures + options seller margin |
| Live policy | CTP/QMT × futures/options for all four market categories |
| Safety | Generic `Futures` refuses China symbols; live bridge gated by `CFFEX_LIVE_TRADING_ENABLED` |

## Full historical OHLCV

Default provider is `auto`: load the complete Sina series (often 10+ years for continuous contracts such as `RB0` / `IF0`), then optionally window by date.

```bash
# HTTP
GET /api/kline/history?market=CNFutures&symbol=RB0&timeframe=1D
GET /api/kline/history?market=CNFutures&symbol=IF2509&timeframe=1D&start_date=2024-01-01&end_date=2024-12-31

# CLI
cd backend_api_python
PYTHONPATH=. python scripts/fetch_cn_futures_history.py --symbol RB0 --timeframe 1D -o rb0.json
```

Notes:
- Root / `*0` codes map to **main continuous** feeds (`RB` → `RB0`).
- Dated contracts (`rb2509`) fetch that delivery month.
- Minute/4H history needs a dated contract on most venues.
- Futures-options history currently uses the underlying continuous series as reference.

## Strategy / trading examples

```json
{ "exchange_id": "ctp", "market_category": "CNFutures", "market_type": "futures", "symbol": "CNFutures:rb2509" }
```

## Visibility

Set `SHOW_CN_FUTURES=true` or include markets in `ENABLED_MARKETS`.

## Tests

```bash
cd backend_api_python
PYTHONPATH=. pytest tests/test_cffex_ctp_qmt_integration.py tests/test_cn_futures_history.py tests/test_broker_market_policy.py -q
```

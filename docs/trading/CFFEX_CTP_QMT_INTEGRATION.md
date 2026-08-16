# Mainland China Futures & Futures Options

**Exchanges**: CFFEX · SHFE · DCE · CZCE · INE · GFEX  
**Markets**: `CNFutures`, `CNFuturesOptions` (plus legacy `CNIndexFutures` / `CNIndexOptions`)  
**Channels**: `ctp`, `qmt`

## Capabilities

| Layer | Detail |
| --- | --- |
| Contract catalog | 60+ mainstream roots in `app/markets/cn_futures.py` |
| Quotes | `CnFuturesDataSource` — `CN_FUTURES_MARKET_DATA_PROVIDER=compliance\|akshare` |
| Open/close runtime | Margin, 今/昨仓, futures + options seller margin |
| Live policy | CTP/QMT × futures/options for all four market categories |
| Safety | Generic `Futures` refuses China symbols; live bridge gated by `CFFEX_LIVE_TRADING_ENABLED` |

## Examples

```json
{ "exchange_id": "ctp", "market_category": "CNFutures", "market_type": "futures", "symbol": "CNFutures:rb2509" }
```

```json
{ "exchange_id": "qmt", "market_category": "CNFuturesOptions", "market_type": "options", "symbol": "CNFuturesOptions:m2509-C-2800" }
```

## Visibility

Set `SHOW_CN_FUTURES=true` or include markets in `ENABLED_MARKETS`.

## Tests

```bash
cd backend_api_python
PYTHONPATH=. pytest tests/test_cffex_ctp_qmt_integration.py tests/test_broker_market_policy.py -q
```

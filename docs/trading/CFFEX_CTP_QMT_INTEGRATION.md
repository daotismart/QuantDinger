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
| Live CTP orders | OpenCTP TdApi (`app.services.ctp_td`) via `CtpClient` when `mode=live` |
| Safety | Generic `Futures` refuses China symbols; live gated by `CFFEX_LIVE_TRADING_ENABLED` |

## CTP live trading (TdApi)

1. Install OpenCTP bindings in the backend image/venv (`pip install openctp-ctp`) and ensure `zh_CN.GB18030` locale if required by the broker stack.
2. Set trader front credentials (or reuse Md credentials where the broker allows):

```bash
CFFEX_LIVE_TRADING_ENABLED=true
CTP_TD_FRONT=tcp://host:port
CTP_TD_BROKER_ID=...
CTP_TD_USER_ID=...
CTP_TD_PASSWORD=...
CTP_TD_APP_ID=...          # when the broker requires ReqAuthenticate
CTP_TD_AUTH_CODE=...
CTP_TD_PRODUCT_INFO=...    # optional UserProductInfo
```

3. Create / bind an exchange credential with `exchange_id=ctp` and `environment=live`
   (UI/API: `POST /api/credentials/create`). Field aliases such as `CTP_USERNAME`,
   `CTP_TRADE_SERVER`, `CTP_ENVIRONMENT=实盘` are accepted. Omitting fields falls back
   to `CTP_TD_*` / `CTP_MD_*` env defaults on the server.
4. Strategy market category must be `CNFutures` / `CNFuturesOptions` (or legacy index aliases). Amount is **lots**.

Smoke-check connection only (no order):

```python
from app.services.live_trading.factory import create_client
client = create_client(
    {"exchange_id": "ctp", "environment": "live", "market_scope": "futures"},
    market_type="futures",
)
print(client.test_connection())
```

Do **not** enable the kill switch or place live orders unless you accept real futures risk.

## Full historical OHLCV

Default provider is `auto`: load the complete Sina series (often 10+ years for continuous contracts such as `RB0` / `IF0`), then optionally window by date.

```bash
# Daily
GET /api/kline/history?market=CNFutures&symbol=RB0&timeframe=1D

# Minute (stitches nearby delivery months; ~1023 bars/contract upstream)
GET /api/kline/history?market=CNFutures&symbol=RB0&timeframe=5m
GET /api/kline/history?market=CNFutures&symbol=RB0&timeframe=1m

# CLI
cd backend_api_python
PYTHONPATH=. python scripts/fetch_cn_futures_history.py --symbol RB0 --timeframe 5m --stitch-months 12 -o rb0_5m.json
```

Notes:
- Root / `*0` codes map to **main continuous** feeds (`RB` → `RB0`).
- Dated contracts (`rb2509`) fetch that delivery month.
- Minute periods: `1m` / `3m` / `5m` / `15m` / `30m` / `1H` / `4H`.
- Full minute history stitches up to `CN_FUTURES_MINUTE_STITCH_MONTHS` (default 12) nearby contracts.
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

# CTP MdApi Tick Market Data

QuantDinger can consume **China futures tick updates** from the Shanghai Futures
Information Technology (上期技术) **CTP MdApi**. This path is **market-data only**;
it does not place CTP orders.

## What is ingested

CTP pushes `OnRtnDepthMarketData` updates. QuantDinger normalizes them into tick
records with last / bid1 / ask1 / volume / open interest / session timestamps, and
exposes:

- a process-local tick cache used by `FuturesDataSource.get_ticker`
- a live `CtpTickPriceFeed` selected when `exchange_id=ctp`
- HTTP helpers under `/api/ctp-md/*`

Strategy signal generation remains completed-bar driven. Live ticks feed
realtime price / risk / special bot price-tick paths, same as crypto public
ticker streams.

## Requirements

1. A reachable CTP **market-data front** (SimNow or broker Md front).
2. An OpenCTP-compatible Python binding, for example:

```bash
pip install openctp-ctp
```

Or set `CTP_MD_API_MODULE` to another module that exports the CTP MdApi surface.

Native CTP libraries are platform-specific. Install them on the host that runs
the trading/legacy process role.

## Configuration

Set these in `backend_api_python/.env` (see `env.example`):

| Variable | Meaning |
| --- | --- |
| `CTP_MD_ENABLED` | `true` to start the shared MdApi gateway |
| `CTP_MD_FRONT` | e.g. `tcp://host:port` |
| `CTP_MD_BROKER_ID` | Broker id |
| `CTP_MD_USER_ID` / `CTP_MD_PASSWORD` | Md login |
| `CTP_MD_APP_ID` / `CTP_MD_AUTH_CODE` | Optional authenticate fields |
| `CTP_MD_INSTRUMENTS` | Boot subscriptions (`rb2505,ag2506,IF2503`) |
| `CTP_MD_FLOW_PATH` | CTP flow directory |
| `CTP_MD_TICK_STALE_AFTER_SECONDS` | Freshness window for cache consumers |

## API

Authenticated human API:

- `GET /api/ctp-md/status`
- `GET /api/ctp-md/ticks`
- `GET /api/ctp-md/tick?symbol=rb2505`
- `POST /api/ctp-md/subscribe` with `{"instruments":["rb2505","IF2503"]}`

## Live runtime wiring

`create_market_price_feed(exchange_id="ctp", ...)` returns `CtpTickPriceFeed`.
The trading executor uses that factory for live price snapshots.

## Safety notes

- No CTP TdApi / order routing is included.
- Credentials stay in env / addon config; do not commit secrets.
- If the OpenCTP binding is missing, the gateway records an error and leaves
  Futures ticker fallbacks (Twelve Data / yfinance / CCXT) unchanged.

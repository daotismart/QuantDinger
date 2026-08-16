# Upstream K-line Sources and Latency by Timeframe

System cache TTLs come from `CacheConfig.KLINE_CACHE_TTL`. Completed-bar delay is inherent to closed-candle semantics. Provider RTT and rate limits are extra.

| TF | App cache TTL | Closed-bar wait | Tick-aggregated |
| --- | ---: | ---: | --- |
| 1m | 3s | ≤60s | Yes (CTP maint only) |
| 3m | 4s | ≤180s | No (often merged from 1m) |
| 5m | 5s | ≤300s | No |
| 15m | 8s | ≤900s | No |
| 30m | 10s | ≤1800s | No |
| 1H | 10s | ≤3600s | No |
| 4H | 15s | ≤14400s | No |
| 1D | 30s | ≤1 session/day | No |
| 1W | 60s | ≤1 week | No |

### Market sources (summary)

| Market | Primary chain | Notes |
| --- | --- | --- |
| Crypto | CCXT OHLCV (+ public venue failover) | May resample 3m/4h/1w when unsupported |
| Futures (traditional) | Twelve Data → yfinance → Tiingo/FX metals | Crypto-futures symbols use CCXT |
| Futures (CN + CTP maint) | Tick→1m aggregate; other TF via factory | Default `get_kline` still uses factory |
| USStock | yfinance | 3m merged from 1m |
| CN/HK | Twelve Data → Tencent(D/W) → yfinance → AkShare | 3m/4H may merge |
| Forex | Twelve Data → Tiingo → yfinance | |
| MOEX | ISS API | 5/15/30m from 1m; 4H from 60m |

Contract tests: `tests/test_kline_timeframe_sources.py`.

# 各周期上游 K 线来源与延迟（当前实现）

> 说明：下列「系统缓存」来自 `CacheConfig.KLINE_CACHE_TTL`，是应用层重复请求的最短复用时间。  
> 「完成 bar 延迟」指策略/图表语义上通常使用**已收盘 K 线**，因此至少等待一个完整周期。  
> 供应商网络 RTT、配额限流不计入下表固定数字。

## 总览

| 周期 | 系统缓存 TTL | 完成 bar 固有延迟 | 是否可由 CTP tick 合成 |
| --- | ---: | ---: | --- |
| 1m | 3s | ≤60s（等当分钟收盘） | **是**（仅维护开启时，国内期货） |
| 3m | 4s | ≤180s | 否（多由 1m 合并/重采样） |
| 5m | 5s | ≤300s | 否 |
| 15m | 8s | ≤900s | 否 |
| 30m | 10s | ≤1800s | 否 |
| 1H | 10s | ≤3600s | 否 |
| 4H | 15s | ≤14400s | 否 |
| 1D | 30s | ≤1 个交易日 | 否 |
| 1W | 60s | ≤1 周 | 否 |

实时最新价（非 K 线）：加密公共 WS / CTP tick 为亚秒～约 1s；`get_realtime_price` 另有 30s 结果缓存。

## 分市场上游链路

### Crypto
- 主源：CCXT 各交易所 `fetch_ohlcv`
- 映射：1m/3m/5m/15m/30m/1H/4H/1D/1W → 交易所原生周期（见 `CCXTConfig.TIMEFRAME_MAP`）
- 回退重采样：交易所若不支持目标周期，可从更细周期合成（如 3m←1m，4H←1H/2H，1W←1D）
- 公开行情可在多所间 failover（live 绑定交易所时关闭）

### Futures（传统美系等）
- 主源链：Twelve Data → yfinance →（贵金属）外汇现货 / Tiingo
- TD 支持：1m/5m/15m/30m/1H/4H/1D/1W
- yfinance：同类周期；延迟与历史深度受 Yahoo 限制（1m 历史很短）
- 加密期货符号：走 CCXT futures

### Futures（国内合约 + CTP 维护）
- 实时 1m：CTP tick 本地合成（`realtime_tick_agg`）
- 其它周期：仍走 `DataSourceFactory` 上游（国内合约若未匹配传统符号表，历史链路可能薄弱，需依赖配置的数据源）

### USStock
- 主源：yfinance（Finnhub 多用于报价/辅助）
- 3m：拉 1m 再每 3 根合并
- 日内分钟线历史窗口受 yfinance 限制（如 1m 约数日）

### CNStock / HKStock
- 有 Twelve Data Key：Twelve Data →（日/周）腾讯 → yfinance → AkShare
- 无 Key：分钟/小时偏 yfinance/AkShare；日/周腾讯优先
- 3m：上游 1m/1min 再合并；4H 在 yfinance 路径可由 1h×4 合并

### Forex
- Twelve Data → Tiingo → yfinance
- TD：1m/5m/15m/30m/1H/4H/1D/1W（及部分 1M）

### MOEX
- MOEX ISS 公共 API
- 原生：1m / 1H / 1D / 1W
- 5m/15m/30m：由 1m 重采样；4H：由 60m 重采样  
  → 这些周期额外叠加重采样计算，但数据新鲜度仍受源间隔约束

## 延迟怎么理解（实用口径）

1. **已完成 K 线**：延迟 ≈ `max(周期长度的收盘等待, 上游更新延迟) + 请求耗时 + 系统缓存 TTL`  
2. **未完成当前 bar**：多数策略路径**故意不用**实时价去改写 OHLC；实时价另走 ticker/CTP  
3. **历史维护**：默认每 300s 回拉并校验入库，只影响 `qd_market_bars`，不改变默认 `get_kline` 读路径

## 相关代码

- 缓存 TTL：`app/config/database.py` → `CacheConfig.KLINE_CACHE_TTL`
- 市场入口：`DataSourceFactory.get_kline` / `KlineService.get_kline`
- 契约测试：`tests/test_kline_timeframe_sources.py`

# 行情数据连续性与准确性维护

QuantDinger 提供**实时**与**历史**两套维护程序，用于保证关注标的的行情连续、OHLC 准确。

## 能力

- 检测 K 线缺口（区分交易时段间隙与数据缺口）
- 入库前校验 OHLC/成交量
- 从上游数据源回补可恢复缺口
- 可选持久化 CTP tick，并聚合成完整 1m K 线
- tick 过期时自动重新订阅

## 启用

```bash
MARKET_DATA_MAINT_ENABLED=true
MARKET_DATA_MAINT_WATCHLIST=Futures:rb2505:1m@ctp:futures
CTP_MD_ENABLED=true
CTP_MD_INSTRUMENTS=rb2505
```

## 进程分工

- **实时**：Trading 进程线程（tick 落库/聚合/重订阅）
- **历史**：Celery Beat 周期任务（拉 K 线、校验、回补）
- **清理**：Celery Beat 按保留天数清理 tick/K 线

详情见英文文档 `MARKET_DATA_MAINT_GUIDE.md` 与 `env.example`。

各周期上游来源与延迟详见 `docs/trading/KLINE_TIMEFRAME_SOURCES_CN.md`。

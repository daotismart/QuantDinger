# 本地数据服务（Local Data Service）

基于 `qd_market_bars` 的本地 K 线服务，并通过 `DataSourceFactory.get_kline` 提供 **本地优先、外部 API 兜底** 的统一读路径。

## 架构

```
采集 / 维护                本地仓库                 消费方
─────────────────         ─────────────           ───────────────
CTP tick → RealtimeMaint  → qd_market_bars    →   DataSourceFactory.get_kline
HistoricalMaint + API     (校验 + upsert)         (LOCAL_BAR_READ_ENABLED)
Bulk ingest script                              →   回测 / 仿真 / 实盘 / 图表
```

## 启用

```bash
# 1. 开启行情维护（写入 qd_market_bars）
MARKET_DATA_MAINT_ENABLED=true
CTP_MD_ENABLED=true

# 2. 开启本地读取（DataSourceFactory 优先读 DB）
LOCAL_BAR_READ_ENABLED=true
LOCAL_BAR_MIN_COVERAGE=0.8
LOCAL_BAR_MAX_STALE_SEC=900
```

UI 管理员可在 **数据服务 → 数据服务** 页切换运行时配置（写入 `qd_data_service_config`）。

## API（`/api/data-service`）

| 模块 | 路径 | 说明 |
|------|------|------|
| 概览 | `GET /overview` | 库存、维护状态、本地读取配置 |
| 采集 | `GET/POST /collection/watchlist` | 监控列表 |
| 采集 | `POST /collection/historical/run` | 触发历史维护 |
| 采集 | `POST /collection/retention/run` | 触发保留清理 |
| 采集 | `GET /collection/runs` | 维护任务审计 |
| 治理 | `GET /governance/inventory` | 按 symbol 统计 bar 数 |
| 治理 | `GET /governance/gaps` | 缺口检测 |
| 治理 | `GET /governance/quality` | quality_flags 汇总 |
| 服务 | `GET/POST /service/config` | 本地读取运行时配置 |
| 服务 | `GET /service/health` | 健康检查 |
| 服务 | `POST /service/preview` | 对比 local / upstream |

## 前端

QuantDinger-Vue 管理员菜单 **数据服务**（`/data-service`），含三个 Tab：数据采集、数据治理、数据服务。

## 注意事项

- 历史维护任务调用 `get_kline(upstream_only=True)`，避免与本地库循环对比。
- 日内 bar 超过 `LOCAL_BAR_MAX_STALE_SEC` 未更新时会回退上游 API。
- 日线/周线不受 stale 限制（仅日内周期检查）。

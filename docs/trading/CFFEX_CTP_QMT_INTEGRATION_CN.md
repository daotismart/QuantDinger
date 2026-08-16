# 中金所股指期货 / 期权集成说明

**范围**: 中金所（CFFEX）股指期货 IF/IH/IC/IM、股指期权 IO/HO/MO  
**通道**: CTP、QMT/miniQMT  
**状态**: 股指**期货**已纳入实盘政策矩阵，并提供保证金 / 开平仓（今仓昨仓）模拟运行时；期权仍为研究 / paper。真实 CTP/QMT 网关需自行接入。

## 交付内容

| 层级 | 说明 |
| --- | --- |
| 合约模型 | `app/markets/cn_index_derivatives.py`：根代码、乘数、最小变动价位、保证金率 |
| 市场模块 | `CNIndexFutures`（含 live）、`CNIndexOptions`（research/backtest/paper） |
| 合规行情 | `app/data_sources/cffex.py`，`CFFEX_MARKET_DATA_PROVIDER=compliance\|akshare` |
| 开平仓运行时 | `app/services/cffex_trading/runtime.py`：保证金、今/昨仓、手续费 |
| 交易通道 | `CtpClient` / `QmtClient`，默认 simulation；实盘需 `CFFEX_LIVE_TRADING_ENABLED=true` + 外部桥 |
| 政策矩阵 | `ctp`/`qmt` × `CNIndexFutures` × `futures` |

## 策略配置示例

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

裸代码（如 `IF2509`）不会再被推断为美股，必须写完整市场前缀。

## 安全边界

- 通用 `Futures` 数据源拒绝 CFFEX 标的，禁止落到 Binance/CME。
- `CNIndexOptions` 不在实盘白名单。
- 未设置 `CFFEX_LIVE_TRADING_ENABLED=true` 且未配置原生桥时，禁止实盘下单。
- 默认不展示：`SHOW_CN_INDEX_DERIVATIVES=true` 或写入 `ENABLED_MARKETS`。

## 测试

```bash
cd backend_api_python
PYTHONPATH=. pytest tests/test_cffex_ctp_qmt_integration.py tests/test_broker_market_policy.py -q
```

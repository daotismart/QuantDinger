# 中国期货及期货期权集成说明

**交易所**: 中金所 CFFEX · 上期所 SHFE · 大商所 DCE · 郑商所 CZCE · 上期能源 INE · 广期所 GFEX  
**市场类别**: `CNFutures`、`CNFuturesOptions`（兼容别名 `CNIndexFutures` / `CNIndexOptions`）  
**通道**: CTP、QMT/miniQMT

## 能力

| 层级 | 说明 |
| --- | --- |
| 合约目录 | `app/markets/cn_futures.py`，覆盖主流商品/股指/国债及可交易期权品种 |
| 行情 | `CnFuturesDataSource`，`CN_FUTURES_MARKET_DATA_PROVIDER=compliance\|akshare` |
| 开平仓运行时 | 保证金、今/昨仓；期权卖方保证金 |
| 实盘政策 | CTP/QMT × futures/options 全市场白名单 |
| 安全 | 通用 `Futures` 拒绝国内品种；实盘需 `CFFEX_LIVE_TRADING_ENABLED=true` + 外部桥 |

## 示例

```json
{ "exchange_id": "ctp", "market_category": "CNFutures", "market_type": "futures", "symbol": "CNFutures:rb2509" }
```

```json
{ "exchange_id": "qmt", "market_category": "CNFuturesOptions", "market_type": "options", "symbol": "CNFuturesOptions:m2509-C-2800" }
```

裸代码（如 `rb2509`）不会推断为美股，必须写市场前缀。

## 可见性

`SHOW_CN_FUTURES=true`，或写入 `ENABLED_MARKETS`。

## 测试

```bash
cd backend_api_python
PYTHONPATH=. pytest tests/test_cffex_ctp_qmt_integration.py tests/test_broker_market_policy.py -q
```

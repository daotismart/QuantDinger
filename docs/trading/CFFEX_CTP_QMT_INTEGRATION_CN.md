# 中国期货及期货期权集成说明

**交易所**: 中金所 CFFEX · 上期所 SHFE · 大商所 DCE · 郑商所 CZCE · 上期能源 INE · 广期所 GFEX  
**市场类别**: `CNFutures`、`CNFuturesOptions`（兼容别名 `CNIndexFutures` / `CNIndexOptions`）  
**通道**: CTP、QMT/miniQMT

## 能力

| 层级 | 说明 |
| --- | --- |
| 合约目录 | `app/markets/cn_futures.py`，覆盖主流商品/股指/国债及可交易期权品种 |
| 行情 / 历史 | `CnFuturesDataSource`，默认 `auto`：akshare 拉取完整日线历史，失败回落 compliance |
| 开平仓运行时 | 保证金、今/昨仓；期权卖方保证金 |
| 实盘政策 | CTP/QMT × futures/options 全市场白名单 |
| 安全 | 通用 `Futures` 拒绝国内品种；实盘需 `CFFEX_LIVE_TRADING_ENABLED=true` + 外部桥 |

## 完整历史行情

```bash
# HTTP（不受普通 /kline 的 1000 条上限限制）
GET /api/kline/history?market=CNFutures&symbol=RB0&timeframe=1D
GET /api/kline/history?market=CNFutures&symbol=IF2509&timeframe=1D&start_date=2024-01-01&end_date=2024-12-31

# CLI
cd backend_api_python
PYTHONPATH=. python scripts/fetch_cn_futures_history.py --symbol RB0 --timeframe 1D -o rb0.json
```

说明：
- 根代码 / `*0` → 主力连续（`RB` → `RB0`），可拿到完整历史（螺纹钢等常超过 4000 根日线）
- 带月份合约（`rb2509`）拉该交割月
- 分钟 / 4H 多数需具体合约月
- 期权历史暂用标的主力连续作参考序列

## 交易示例

```json
{ "exchange_id": "ctp", "market_category": "CNFutures", "market_type": "futures", "symbol": "CNFutures:rb2509" }
```

裸代码（如 `rb2509`）不会推断为美股，必须写市场前缀。

## 可见性

`SHOW_CN_FUTURES=true`，或写入 `ENABLED_MARKETS`。

## 测试

```bash
cd backend_api_python
PYTHONPATH=. pytest tests/test_cffex_ctp_qmt_integration.py tests/test_cn_futures_history.py tests/test_broker_market_policy.py -q
```

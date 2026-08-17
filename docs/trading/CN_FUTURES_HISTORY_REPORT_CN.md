# 中国期货完整历史行情数据报告

**生成时间**: 2026-08-16 18:28:29 CST  
**数据源**: akshare/auto (Sina futures_zh_daily_sina / futures_main_sina)  
**抽样成功**: 16/16  
**合计K线**: 47130 根日线  
**覆盖区间**: 2005-01-04 → 2026-08-14

## 1. 合约目录规模

| 交易所 | 期货品种根 | 含期权品种 |
| --- | ---: | ---: |
| CFFEX | 8 | 0 |
| CZCE | 17 | 8 |
| DCE | 19 | 8 |
| GFEX | 3 | 2 |
| INE | 5 | 1 |
| SHFE | 17 | 8 |
| **合计根代码** | **72** | — |

## 2. 完整历史抽样结果（日线）

| 交易所 | 代码 | 名称 | 喂价符号 | 模式 | 根数 | 起始 | 结束 | 最新收盘 |
| --- | --- | --- | --- | --- | ---: | --- | --- | ---: |
| CFFEX | `IF0` | 沪深300股指期货主力连续 | `IF0` | continuous | 2324 | 2017-01-17 | 2026-08-14 | 4620.4 |
| CFFEX | `IM0` | 中证1000股指期货主力连续 | `IM0` | continuous | 986 | 2022-07-22 | 2026-08-14 | 7650.2 |
| CFFEX | `T0` | 10年期国债期货主力连续 | `T0` | continuous | 2324 | 2017-01-17 | 2026-08-14 | 109.54 |
| SHFE | `RB0` | 螺纹钢主力连续 | `RB0` | continuous | 4222 | 2009-03-27 | 2026-08-14 | 3015.0 |
| SHFE | `AU0` | 黄金主力连续 | `AU0` | continuous | 4531 | 2008-01-09 | 2026-08-14 | 943.16 |
| SHFE | `CU0` | 铜主力连续 | `CU0` | continuous | 5258 | 2005-01-04 | 2026-08-14 | 107690.0 |
| DCE | `M0` | 豆粕主力连续 | `M0` | continuous | 5261 | 2005-01-04 | 2026-08-14 | 3165.0 |
| DCE | `I0` | 铁矿石主力连续 | `I0` | continuous | 3119 | 2013-10-18 | 2026-08-14 | 710.5 |
| CZCE | `SR0` | 白糖主力连续 | `SR0` | continuous | 5002 | 2006-01-12 | 2026-08-14 | 5309.0 |
| CZCE | `TA0` | PTA主力连续 | `TA0` | continuous | 4776 | 2006-12-19 | 2026-08-14 | 5776.0 |
| INE | `SC0` | 原油主力连续 | `SC0` | continuous | 2036 | 2018-03-26 | 2026-08-14 | 556.2 |
| GFEX | `SI0` | 工业硅主力连续 | `SI0` | continuous | 883 | 2022-12-22 | 2026-08-14 | 8795.0 |
| GFEX | `LC0` | 碳酸锂主力连续 | `LC0` | continuous | 744 | 2023-07-21 | 2026-08-14 | 155240.0 |
| SHFE | `RB2509` | 螺纹钢2509合约 | `RB2509` | contract | 239 | 2024-09-19 | 2025-09-11 | 2941.0 |
| CFFEX | `IF2509` | IF2509合约 | `IF2509` | contract | 164 | 2025-01-20 | 2025-09-19 | 4510.0 |
| DCE | `M2509-C-2800` | 豆粕期权(标的连续参考) | `M0` | continuous | 5261 | 2005-01-04 | 2026-08-14 | 3165.0 |

## 3. 生产全市场入库（2026-08-17）

在生产 `quantdinger-backend` 对目录内 **69** 个期货主力连续（跳过 IO/HO/MO 期权专用根）拉取 Sina/akshare 日线，周线由日线重采样，校验后写入 `qd_market_bars`。

| 项 | 结果 |
| --- | --- |
| 状态 | **69/69 成功**，失败 0 |
| 耗时 | 227.5 秒 |
| 写入行 | 235,214（含日线 + 周线 upsert） |
| Watch | 138 条（每品种 `1D` + `1W`） |
| 覆盖区间 | 2005-01-04 → 2026-08-17 |

| 市场 | 周期 | 品种数 | K 线数 |
| --- | --- | ---: | ---: |
| CNIndexFutures | 1D | 4 | 7,961 |
| CNIndexFutures | 1W | 4 | 1,696 |
| CNFutures | 1D | 65 | 185,879 |
| CNFutures | 1W | 65 | 39,678 |

按交易所：CFFEX 8、SHFE 17、DCE 19、CZCE 17、INE 5、GFEX 3。最短序列为广期所工业硅后续品种 `PS0`（397 根日线，2024-12-26 起）。分钟线未做全市场拼接（新浪单合约约 1023 根，全市场成本过高）。

## 4. 获取方式

```bash
# HTTP
GET /api/kline/history?market=CNFutures&symbol=RB0&timeframe=1D

# CLI
cd backend_api_python
PYTHONPATH=. python scripts/fetch_cn_futures_history.py --symbol RB0 --timeframe 1D -o rb0.json

# 全市场主力连续入库（日线 + 由日线重采样的周线）
PYTHONPATH=. python scripts/ingest_cn_futures_history.py --persist --timeframes 1D,1W

# 全市场分钟线：拉 1m 并本地重采样 5m/15m/30m/1H（拼接邻近交割月）
PYTHONPATH=. python scripts/ingest_cn_futures_history.py --persist --timeframes 1m,5m,15m,30m,1H --stitch-months 12
```

## 5. 结论

- 六大期交所历史日线抽样覆盖: **CFFEX, CZCE, DCE, GFEX, INE, SHFE**
- 生产已入库全部 69 个主力连续的日线与周线（见第 3 节）
- 主力连续（`*0`）可返回完整可获得历史；带月份合约返回该交割月序列。
- 期权代码当前以标的主力连续作为参考历史序列。
- 分钟线可通过跨交割月拼接获得多月历史（见第 6 节）。


## 6. 分钟线历史抽样（跨合约拼接）

**拼接月数**: 8  | **生成时间**: 2026-08-16 18:33:53 CST

| 交易所 | 代码 | 周期 | 根数 | 起始 | 结束 |
| --- | --- | --- | ---: | --- | --- |
| SHFE | `RB0` | 5m | 10459 | 2025-10-21 14:25 | 2026-08-14 23:00 |
| SHFE | `RB0` | 1m | 11236 | 2025-11-04 21:44 | 2026-08-14 23:00 |
| DCE | `M0` | 15m | 5285 | 2025-08-28 14:00 | 2026-08-14 23:00 |
| CFFEX | `IF0` | 5m | 11253 | 2024-02-07 13:50 | 2026-08-14 15:00 |
| INE | `SC0` | 5m | 11253 | 2025-10-16 23:35 | 2026-08-17 00:00 |
| GFEX | `SI0` | 5m | 8922 | 2025-09-29 13:55 | 2026-08-14 15:00 |

说明：新浪单合约约 1023 根；通过拼接邻近交割月可得到多月分钟历史。

```bash
GET /api/kline/history?market=CNFutures&symbol=RB0&timeframe=5m
PYTHONPATH=. python scripts/fetch_cn_futures_history.py --symbol RB0 --timeframe 5m --stitch-months 12 -o rb0_5m.json
```

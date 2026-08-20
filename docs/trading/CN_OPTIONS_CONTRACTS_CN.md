# 中国在市期权合约接入

QuantDinger 将 **CTP 全部在市期权** 写入品种目录，供搜索与按需行情。
**不会**用 CTP Md 全订期权链（交易所订阅上限通常约 500 个合约），也 **不会**
把两万余张合约的历史 K 线批量写入 `qd_market_bars`。

## 市场类别

| 市场 | 内容 |
| --- | --- |
| `CNFuturesOptions` | 商品期货期权（上期所 / 大商所 / 郑商所 / 能源中心 / 广期所）+ 品种根 |
| `CNIndexOptions` | 中金所 IO/HO/MO 在市合约；上交所/深交所 ETF 期权（8 位数字代码，仅搜索） |

ETF 期权只进搜索，不走期货 CTP 下单格式。商品/股指期权下单代码按交易所组装：

| 交易所 | InstrumentID 示例 |
| --- | --- |
| 大商所 / 广期所 | `m2609-C-2800` / `lc2610-C-100000` |
| 上期所 / 能源中心 | `cu2609C100000` / `sc2610C350` |
| 中金所 | `HO2608-C-2500` |
| 郑商所 | `AP610C10000` |

目录里的搜索代码统一为大写带连字符（`M2609-C-2800`），下单时
`format_instrument_id` 转成该所 CTP 合约号。

## 同步

```bash
cd backend_api_python
PYTHONPATH=. python scripts/sync_cn_option_contracts.py
# 或
PYTHONPATH=. python scripts/sync_market_symbols.py --markets CNFutures CNFuturesOptions CNIndexFutures CNIndexOptions
```

`CN_OPTIONS_INCLUDE_ETF=false` 可跳过 ETF 期权。
`CN_OPTIONS_CTP_SYNC=false` 只保留静态品种根。

数据源：AkShare `option_contract_info_ctp()`（`合约状态=1`）。
下次成功同步时，带 `instrument_id` 的旧在市合约会被停用；品种根
（`instrument_id` 为空）保持可搜。

## 行情

日线/周线：先试 `option_commodity_hist_sina`，失败再回退标的主力连续
（`M0`；IO/HO/MO 分别对应 `IF0`/`IH0`/`IM0`）。分钟线始终用标的连续。

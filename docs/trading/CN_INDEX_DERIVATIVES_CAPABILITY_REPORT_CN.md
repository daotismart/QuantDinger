# A 股股指期货 / 股指期权交易能力测试报告

**仓库**: QuantDinger  
**测试日期**: 2026-08-16  
**范围**: 中金所（CFFEX）股指期货 IF/IH/IC/IM，股指期权 IO/HO/MO  
**结论**: **当前不支持实盘交易，也不具备可用的专用行情与合约主数据链路。**

自动化回归见 `backend_api_python/tests/test_cn_index_derivatives_capability.py`。

---

## 1. 测试对象

| 品种 | 交易所 | 代码根 | 本次抽样 |
| --- | --- | --- | --- |
| 沪深300股指期货 | CFFEX | IF | `IF`, `IF2509` |
| 上证50股指期货 | CFFEX | IH | `IH`, `IH2509` |
| 中证500股指期货 | CFFEX | IC | `IC`, `IC2509` |
| 中证1000股指期货 | CFFEX | IM | `IM`, `IM2509` |
| 沪深300股指期权 | CFFEX | IO | `IO`, `IO2509-C-4000` |
| 上证50股指期权 | CFFEX | HO | `HO`, `HO2509P2800` |
| 中证1000股指期权 | CFFEX | MO | `MO`, `MO2509-C-5500` |

---

## 2. 能力矩阵（实测）

| 能力层 | 股指期货 | 股指期权 | 说明 |
| --- | --- | --- | --- |
| 市场模块 | 部分借用 `Futures` | **无** `Options` 模块 | `MARKET_MODULES` 仅有 Crypto/USStock/CNStock/HKStock/Forex/Futures/MOEX |
| 标的主数据 | 未收录 IF/IH/IC/IM | 未收录 IO/HO/MO | `fetch_futures_symbols()` 只有 CME 风格根代码（ES/GC/CL…） |
| 行情数据源 | **拒绝**（安全防护） | **拒绝** | 修复前 `IF` 会被当成加密货币期货打到 Binance |
| 策略标的解析 | 无裸代码推断；需显式前缀 | 同左 | 裸代码 `IF2509` 不再误判为美股 |
| 回测 / 研究 | `Futures` 名义可写，但无 CFFEX 数据 | 不可用 | 无可用 K 线 / 合约日历 / 保证金模型 |
| Paper | 模块特性含 paper，但无落地执行器 | 不可用 | 无对应撮合与持仓模型 |
| 实盘交易 | **阻断** | **阻断** | `LIVE_MARKET_CATEGORIES = {Crypto, USStock}` |
| 券商适配 | 无 CTP / 无 miniQMT / 无期货公司通道 | 同左 | `ctp` 报 `Unknown exchange_id`；已知券商仅为 ibkr/alpaca + 加密货币所 |

---

## 3. 关键明细

### 3.1 实盘策略配置被策略性地拒绝

`validate_strategy_config` 对 `Futures` / `CNStock` / 未知 `Options` 一律抛出“不支持实盘 / analysis-only”。  
`list_supported_brokers_for_market("Futures")` 与 `("Options")` 均为空集。

### 3.2 没有股指期权市场面

代码中不存在 `Options` 市场模块、期权 Greeks、行权价链、到期日滚动或权利仓位模型。`CNStock` 仅为 A 股现货（equity），不能承载股指期权。

### 3.3 期货主数据与行情不覆盖中金所

`FuturesDataSource` 传统期货白名单来自 Twelve Data / yfinance（CME/CBOT/NYMEX 等）。  
CFFEX 根代码不在白名单；若放行会错误走 CCXT/Binance 加密期货路径（本次测试中 Binance 返回 451 地区限制）。  
现已增加显式 `ValueError`，避免静默错路由。

### 3.4 标的推断曾存在误分类风险（已加固）

修复前：`infer_market("IF2509")` 因通用美股正则被判为 `USStock`。  
修复后：CFFEX 股指期货/期权裸代码不再推断市场，必须写完整前缀；即便写成 `Futures:IF2509`，行情层仍会明确拒绝。

### 3.5 A 股现货能力不能替代衍生品

`CNStock` 支持研究 / 回测 / paper 特性声明，实盘同样被政策层拦截，且标的空间是股票代码（如 `600519.SH`），与 IF/IO 合约体系无关。

---

## 4. 测试执行

```bash
cd backend_api_python
PYTHONPATH=. pytest tests/test_cn_index_derivatives_capability.py -q
```

期望：全部通过。该文件把“不支持”固化为回归断言，防止后续误开实盘或再次把 IF 路由到加密货币交易所。

---

## 5. 若要真正支持，需要补齐的子系统

按依赖顺序（实现量由小到大）：

1. **市场与合约模型**：新增 `CNIndexFutures` / `CNIndexOptions`（或统一 `CFFEX`）模块、合约月份、乘数、最小变动价位、交易日历。  
2. **行情**：中金所/期货公司/合规数据商的 tick 与 K 线；期权还需要希腊值与隐含波动率。  
3. **交易通道**：CTP 或券商 QMT/miniQMT 等国内期货 API；账户、保证金、强平、手续费。  
4. **风控与合规**：投资者适当性、夜盘/日盘时段、持仓限额、期权卖方保证金。  
5. **策略运行时**：双向开平、今仓/昨仓、权利金结算、到期交割。  
6. **策略政策矩阵**：把对应 `exchange_id` 与 `LIVE_MARKET_CATEGORIES` 显式纳入，而不是复用 `Futures:ES` 路径。

在未完成以上项之前，任何“用 Crypto/IBKR/Futures:ES 代理交易 A 股股指衍生品”的做法都不成立。

---

## 6. 总结

| 问题 | 结果 |
| --- | --- |
| 能否测试并完成 A 股股指期货实盘下单？ | **否** |
| 能否测试并完成 A 股股指期权实盘下单？ | **否** |
| 现有 `Futures` 能否当中金所用？ | **否**（仅 CME/加密风格研究标的） |
| 本次交付 | 能力报告 + 回归测试 + CFFEX 错路由/误分类防护 |

**总评：QuantDinger 当前对 A 股股指期货与股指期权的交易能力为 0（未实现）。** 可继续用于 A 股现货研究（`CNStock`）及海外/加密期货研究，但不能用于中金所股指衍生品交易验证。

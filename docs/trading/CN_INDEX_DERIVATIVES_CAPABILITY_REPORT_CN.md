# A 股股指期货 / 股指期权能力报告（已由 main 超限）

**原始测试日期**: 2026-08-16  
**本修订**: 2026-08-17（合并 `origin/main` 后）  
**范围**: 中金所 IF/IH/IC/IM、IO/HO/MO

---

## 状态说明

本报告最初结论为「QuantDinger 对中金所股指期货/期权能力为 0」。  
在本分支合入期间，`main` 已通过 PR #2 / #3 等落地 **CTP/QMT 通道、CNFutures 目录、行情与实盘政策**，因此 **原结论已过时，以下以当前 `main` 能力为准**。

权威文档请改读：

- `docs/trading/CFFEX_CTP_QMT_INTEGRATION_CN.md`
- `docs/trading/CTP_MD_GUIDE_CN.md`
- `docs/trading/CN_FUTURES_HISTORY_REPORT_CN.md`

回归测试请改跑：

```bash
cd backend_api_python
PYTHONPATH=. pytest tests/test_cffex_ctp_qmt_integration.py tests/test_cn_futures_history.py tests/test_broker_market_policy.py -q
```

---

## 合并时仍成立的安全边界

这些与「是否已支持交易」无关，合并后仍应保持：

| 边界 | 说明 |
| --- | --- |
| 裸代码不推断为美股 | `IF2509` / `IO2509-C-4000` 等不得落入 `USStock` 正则 |
| 通用 `Futures` 数据源拒国内品种 | 不得把 IF/IO 静默打到 Twelve Data / yfinance / Binance |
| 实盘需专用通道 | `ctp` / `qmt` + `CNFutures` / `CNFuturesOptions`（或 `CNIndex*` 别名） |
| 兼容模块 | `app.markets.cn_index_derivatives` 仅为薄封装，新代码应使用 `app.markets.cn_futures` |

---

## 意图冲突记录（供评审）

| 本分支原意图 | `main` 当前意图 | 处理 |
| --- | --- | --- |
| 固化「未实现」能力缺口报告与拒绝路径 | 实现 CFFEX/国内期货实盘与行情 | 代码冲突处采用 `main`；删除过时「能力为 0」测试；本报告改为超限说明 |

若仍需审计「未接真实期货公司前的缺口」，请基于 `CFFEX_CTP_QMT_INTEGRATION_CN.md` 中的合规桥接与 `CFFEX_LIVE_TRADING_ENABLED` 开关单独评估，而不是沿用本文旧结论。

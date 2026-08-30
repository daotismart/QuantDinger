# GEX + LSP + Kelly 次月宽跨式卖方回测（588000 科创50ETF）

## 1. 回测结论（摘要）

| 项 | 结果 |
|----|------|
| 标的 | **588000（科创50ETF）** 及其 ETF 期权 |
| 区间 | 2026-03-30 → 2026-08-28（与期权链/持仓量对齐后约 90 个交易日） |
| 初始资金 | 1,000,000 |
| 期末权益 | 947,160.01 |
| 总收益 | **-5.28%** |
| 年化波动 | 4.72% |
| Sharpe | -3.23 |
| 最大回撤 | **-5.57%** |
| 交易笔数 | 12（胜率 33.3%） |
| 平均单笔盈亏 | -4,403 |
| 定仓 | Kelly 保证金占比（`f*=2p-1`，p 来自 BS 腿胜率） |
| 合约月 | **次月**；到期前 **15 DTE** 移仓 |
| 对冲 | **纯期权**（现货 588000 不下单） |

本期 588000 样本偏趋势/破墙：12 笔中多次 `call_wall_breach` / `put_wall_breach`，卖方宽跨在单边行情下承压。

原始 JSON：`docs/reports/GEX_LSP_KELLY_STRANGLE_588000.json`

---

## 2. 配置标的是什么？

**策略配置标的 = ETF 期权对应的现货 ETF**，此处为：

- `CNStock:588000`（科创50ETF）
- 交易的是该 ETF 的 **次月认购/认沽**
- 现货只用于：GEX 墙定位、LSP、IV/波动、BS 胜率；**永不买卖现货**

换标的时（如 510050 / 510300）：选对应 ETF，并换同一标的次月期权链与墙参数。

---

## 3. 策略逻辑（完整）

策略是 **ETF 期权次月宽跨式卖方**，四块分工：

```
588000 现货行情 ──┬── GEX walls ── 安全行权价（call wall / put wall）
                  ├── IV rank   ── 是否够贵才卖权
                  ├── BS d2     ── 各腿虚值概率 → Kelly 的 p
                  └── LSP score ── 净 delta 方向 → call/put 张数偏斜
                                      │
                         Kelly f*=2p-1 → 保证金/权益 → 基础张数
                                      │
                         卖出宽跨：-call / -put（次月），现货仓位恒为 0
```

### 3.1 GEX 墙：卖在哪里

用期权链 Gamma×持仓量估计 **call wall / put wall**：

- 卖出 **OTM call ≈ call wall**、**OTM put ≈ put wall**（宽跨安全宽度）
- **开仓条件**：现货落在两墙内侧（带 `wall_buffer_pct`，默认 0.5%）
- **破墙平仓**：现货突破 call 上缓冲或 put 下缓冲 → `call_wall_breach` / `put_wall_breach`

意图：赌现货在墙内震荡，卖方收权利金；破墙则止损式离场。

### 3.2 高 IV 过滤：什么时候卖

仅当 ATM IV-rank ≥ `iv_rank_min`（默认 0.60）才开新仓。  
权利金偏贵时做空波动；IV 偏低时空仓等待。

### 3.3 Kelly：开多少（胜率来自 BS 腿）

权利金盈亏比按 **1:1**，Kelly：

\[
f^* = 2p - 1
\]

**胜率 p 不再用先验**，而用 Black–Scholes **期权腿胜率**（卖权胜利 = 到期仍虚值）：

| 腿 | 公式 |
|----|------|
| 短 call | \(p_c = N(-d2_c)=P(S_T < K_c)\) |
| 短 put | \(p_p = N(d2_p)=P(S_T > K_p)\) |
| 默认合成 | \(p=\dfrac{C p_c + P p_p}{C+P}\)（权利金加权） |

可选：`average`、`both_otm`（两腿同时虚值 \(p_c+p_p-1\)）。

然后：

1. \(f=\min(f^*, kelly\_max\_fraction)\)（默认封顶 25% 保证金/权益）
2. `base_lots = floor(权益 × f / 单组宽跨保证金)`，再封顶 `kelly_max_lots`
3. \(\sigma\)：优先 ATM IV，否则现货实现波动；\(T\)：剩余到期；\(K\)：墙/腿行权价

### 3.4 LSP：方向敞口（不碰现货）

用现货量价算 LSP 得分 ∈ [-1,1]：

- `score > 0`（偏多）→ **多卖 put / 少卖 call**
- `score < 0`（偏空）→ **多卖 call / 少卖 put**
- 偏斜张数受 `lsp_max_skew_lots` 限制

净 delta 只通过期权张数差实现；**现货目标仓位恒为 0**。

### 3.5 合约月与移仓

- 开仓：**次月**（第二近月）
- 移仓：持仓 DTE ≤ **15** → 平仓并换新次月（`roll_month`）
- 其它退出：破墙、最长持有、样本期末强平（`eod_force_close`）

---

## 4. 关键参数（本次回测）

| 参数 | 值 | 含义 |
|------|-----|------|
| `underlying` | 588000 | 配置标的 ETF |
| `expiry_month` | next | 次月合约 |
| `roll_before_dte` | 15 | 到期前 15 日移仓 |
| `iv_rank_min` | 0.60 | 高 IV 门槛 |
| `kelly_win_prob_mode` | credit_weighted | BS 腿胜率权利金加权 |
| `kelly_max_fraction` | 0.25 | 保证金/权益硬顶 |
| `kelly_max_lots` | 10 | 最大基础张数 |
| `lsp_max_skew_lots` | 1 | LSP 偏斜上限 |
| `wall_buffer_pct` | 0.005 | 破墙缓冲 |
| `multiplier` | 10000 | 合约乘数 |
| `option_margin_rate` | 0.12 | 保证金估算 |

---

## 5. 成交明细（12 笔）

| 开仓 | 平仓 | Put/Call 行权价 | 张数(P/C) | PnL | 原因 |
|------|------|-----------------|-----------|-----|------|
| 2026-04-02 | 2026-04-30 | 1.15 / 1.60 | 11 / 9 | -6,313 | call_wall_breach |
| 2026-04-30 | 2026-05-13 | 1.35 / 1.85 | 11 / 9 | -7,685 | call_wall_breach |
| 2026-05-14 | 2026-05-19 | 1.60 / 1.85 | 11 / 9 | -2,218 | call_wall_breach |
| 2026-05-26 | 2026-06-11 | 1.75 / 2.00 | 9 / 11 | +2,264 | roll_month |
| 2026-06-12 | 2026-06-18 | 1.70 / 1.95 | 9 / 11 | -7,304 | call_wall_breach |
| 2026-06-18 | 2026-06-25 | 1.80 / 2.15 | 11 / 9 | -20,335 | call_wall_breach |
| 2026-06-25 | 2026-06-30 | 1.90 / 2.30 | 11 / 9 | +1,965 | call_wall_breach |
| 2026-07-02 | 2026-07-09 | 1.90 / 2.30 | 11 / 9 | +3,637 | call_wall_breach |
| 2026-07-09 | 2026-07-15 | 2.10 / 2.55 | 11 / 9 | -5,979 | put_wall_breach |
| 2026-07-15 | 2026-07-17 | 1.90 / 2.55 | 9 / 11 | -10,658 | put_wall_breach |
| 2026-07-21 | 2026-07-23 | 1.90 / 2.55 | 9 / 11 | -2,377 | put_wall_breach |
| 2026-07-23 | 2026-08-28 | 1.10 / 2.55 | 11 / 9 | +2,162 | eod_force_close |

观察：

1. **破上墙偏多**：前段多次 `call_wall_breach`，科创50上行阶段对卖方 call 不利。  
2. **中后段破下墙**：7 月出现连续 `put_wall_breach`。  
3. Kelly 常给出约 9–11 张基础仓；LSP 在 ±1 张内偏斜。  
4. 唯一明确移仓盈利笔：`2026-05-26 → 06-11`（`roll_month`，+2,264）。

---

## 6. 一句话

对 **588000**：在墙内、高 IV 时卖次月宽跨；**BS 腿虚值概率**定 Kelly 仓位；**LSP** 调 call/put 不对称；到期前 15 天换月；现货只做信号。  
本段样本趋势破墙频繁，总收益约 **-5.3%**，回撤约 **-5.6%**。

## 7. 复现命令

```bash
# 数据：ClickHouse etf_options → tmp/gex_lsp_strangle/{underlying,chain,oi}_588000.csv
PYTHONPATH=backend_api_python python backend_api_python/scripts/backtest_gex_lsp_short_strangle.py \
  --data-dir tmp/gex_lsp_strangle \
  --underlying 588000 \
  --capital 1000000 \
  --iv-rank-min 0.60 \
  --kelly-max-fraction 0.25 \
  --kelly-max-lots 10
```

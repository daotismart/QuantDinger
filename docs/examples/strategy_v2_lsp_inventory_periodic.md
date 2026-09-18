# LSP 库存管理 · 定周期盘口交易

Strategy API V2 示例：用通达信风格 **LSP**（有符号路径量能）做库存目标，按固定 K 线周期在盘口价附近调仓。

## 逻辑

1. 用双窗口 LSP（`days_1` / `days_2`）从 OHLCV 计算库存分数 `inventory_score ∈ [-1, 1]`  
   - LSP 高 → 买盘拥挤 → 降低库存  
   - LSP 低 → 提高库存  
2. `long_only=true` 时目标仓位裁剪到 `[0, max_position_pct]`  
3. 每 `rebalance_every` 根 K 线调仓一次：  
   - `fill_mode=take`：市价 `order_target_percent`（吃单，滑点近似穿越价差）  
   - `fill_mode=make`：在 mid±半价差挂限价（bid 买 / ask 卖）

默认标的：`USStock:SPY`，周期 `1h`。改源码顶部 `SYMBOL` / `BAR_FREQUENCY` 即可换市场。

## 参数

| 参数 | 默认 | 说明 |
|------|------|------|
| days_1 | 5 | 短 LSP 窗口 |
| days_2 | 10 | 长 LSP 窗口 |
| rebalance_every | 4 | 每隔 N 根 K 线交易 |
| max_position_pct | 0.95 | 最大目标权重 |
| long_only | true | 仅做多库存 |
| deadband_pct | 0.05 | 误差小于此值不调仓 |
| book_spread_bps | 4 | 半价差（bp，make 模式） |
| fill_mode | take | `take` / `make` |
| min_lsp_bars | 30 | 最少历史根数 |

## 回测

```bash
cd backend_api_python
PYTHONPATH=. python scripts/backtest_lsp_inventory_periodic.py
PYTHONPATH=. python scripts/backtest_lsp_inventory_periodic.py --fill-mode make --rebalance-every 3
PYTHONPATH=. python -m pytest tests/test_lsp_inventory_periodic_strategy.py -q
```

也可把 `strategy_v2_lsp_inventory_periodic.py` 粘贴到策略 IDE 验证后跑 UI 回测。若有真实 OHLCV CSV：

```bash
PYTHONPATH=. python scripts/backtest_lsp_inventory_periodic.py --csv /path/to/ohlcv.csv --symbol USStock:SPY
```

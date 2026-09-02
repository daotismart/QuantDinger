"""GEX-TV Iron Condor — listed-chain, defined risk.

Each session the engine reads the then-listed 50ETF option book, picks the
expiry closest to ~45 DTE (28–65 window, roll at 10 DTE), computes GEX walls,
and shorts 14–25Δ call/put **outside** the walls with 3-step long wings
(min 2 if the book is truncated). Net credit must be at least 15% of wing
width. Contracts are NEVER hard-coded.

This source is compiled by Strategy API V2. Backtest Center routes
strategy_family=options_short_vol_iron_condor to the listed-chain research
engine (ClickHouse opt_* / GEX_LSP_DATA_DIR CSVs).
"""

# @param lots int 80 Base lots cap (then risk_cap / Kelly) range=1:200:1
# @param wing_steps int 3 Exchange steps beyond the short for long wings range=1:5:1
# @param min_credit_to_width float 0.15 Skip thin credit / wing range=0:0.5:0.05
# @param min_short_delta float 0.14 Short-leg |Δ| floor range=0.05:0.3:0.01
# @param max_short_delta float 0.25 Short-leg |Δ| cap range=0.1:0.4:0.01
# @param target_dte int 45 Preferred DTE range=21:70:1
# @param roll_before_dte int 10 Flatten when DTE falls to this range=5:30:1
# @param risk_cap float 0.06 Max loss / NAV per condor range=0.01:0.2:0.01
# @param expiry_month str target target≈45 DTE; next=次月; front=当月
# @param max_hold_bars int 60 Flatten after N daily bars range=1:90:1
# @param take_profit_pct float 0.75 Close when 75% of credit is captured range=0.1:0.9:0.05
# @param stop_loss_pct float 0.9 Close when MTM loss >= stop * max risk range=0.3:1.5:0.05
# @param require_high_iv bool 0 Require IV-rank ≥ 40 to sell premium
# @param require_inside_walls bool 0 Require spot inside GEX walls to enter
# @param exit_on_wall_breach bool 0 Flatten when spot breaches GEX walls
# @param kelly bool 1 Enable Kelly cap on top of risk_cap
# @param kelly_max_fraction float 0.10 Kelly fraction cap range=0.05:0.5:0.05
# @param kelly_max_lots int 80 Max lots after Kelly / risk_cap range=1:200:1
# @param max_skew_lots int 0 Extra short lots tilted by LSP range=0:5:1

PERSIST_RUNTIME_STATE = True

UNDERLYING_CODE = "510050"
UNDERLYING_SYMBOL = "CNStock:510050.SH"
BAR_FREQUENCY = "1d"


def initialize(context):
    g.underlying_symbol = UNDERLYING_SYMBOL
    g.underlying_code = UNDERLYING_CODE
    context.set_universe([g.underlying_symbol])
    context.set_benchmark(g.underlying_symbol)
    context.subscribe(frequency=BAR_FREQUENCY, fields=["open", "high", "low", "close", "volume"])
    context.set_warmup(30)
    context.set_metadata(
        direction_mode="both",
        strategy_family="options_short_vol_iron_condor",
        underlying=UNDERLYING_CODE,
        expiry_month="target",
        contract_selection="listed_chain_gex_walls",
        engine="gex-lsp-iron-condor-research",
        pick_model="gex_tv_iron_condor",
    )


def handle_data(context, data):
    """Compile stub. Listed-chain GEX-TV selection runs in the research engine.

    The engine, each bar:
      1. take the option contracts listed that day for 510050
      2. pick expiry closest to 45 DTE (28–65)
      3. GEX walls → 14–25Δ shorts outside walls, 3-step listed wings (min 2), credit/width ≥ 15%
      4. size by 6% NAV risk cap (Kelly as a further cap) and roll at 10 DTE
      5. take profit when 75% of credit is captured; skip flatten if any leg quote is missing
    """
    if not is_trade() or context.current_dt is None:
        return
    spot = float(data.current(g.underlying_symbol, "close") or 0.0)
    if spot <= 0:
        return

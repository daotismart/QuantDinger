"""GEX+LSP Iron Condor — listed-chain, defined risk.

Each session the engine reads the then-listed 50ETF option book (次月优先),
computes GEX walls, shorts the near-wall call/put and buys one further-OTM
wing. Contracts are NEVER hard-coded: expired months roll off and new strikes
appear automatically.

This source is compiled by Strategy API V2. Backtest Center routes
strategy_family=options_short_vol_iron_condor to the listed-chain research
engine (ClickHouse opt_* / GEX_LSP_DATA_DIR CSVs).
"""

# @param lots int 120 Base lots per short side range=1:200:1
# @param wing_steps int 1 Listed strikes beyond the short for long wings range=1:5:1
# @param expiry_month str next Front=当月, next=次月
# @param max_hold_bars int 60 Flatten after N daily bars range=1:90:1
# @param take_profit_pct float 0.5 Close remaining debit <= (1-tp)*entry credit range=0.1:0.9:0.05
# @param stop_loss_pct float 0.9 Close when MTM loss >= stop * max risk range=0.3:1.5:0.05
# @param require_high_iv bool 0 Require elevated IV-rank to sell premium
# @param require_inside_walls bool 0 Require spot inside GEX walls to enter
# @param kelly bool 0 Enable Kelly sizing instead of fixed lots
# @param kelly_max_fraction float 0.25 Kelly fraction cap range=0.05:0.5:0.05
# @param kelly_max_lots int 150 Max lots after Kelly range=1:200:1
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
        expiry_month="next",
        contract_selection="listed_chain_gex_walls",
        engine="gex-lsp-iron-condor-research",
    )


def handle_data(context, data):
    """Compile stub. Listed-chain selection runs in the research engine.

    The engine, each bar:
      1. take the option contracts listed that day for 510050
      2. pick 次月 expiry (fallback 当月)
      3. GEX walls → short call/put, long one listed strike further OTM
      4. size 120 lots (or Kelly) and roll ~15 DTE
    """
    if not is_trade() or context.current_dt is None:
        return
    spot = float(data.current(g.underlying_symbol, "close") or 0.0)
    if spot <= 0:
        return

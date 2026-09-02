"""Strategy/indicator param coercion — keep round() from seeing complex values."""

from app.services.indicator_params import IndicatorParamsParser
from app.services.param_values import coerce_param_value, merge_declared_params
from app.services.strategy_v2 import StrategyV2BacktestRunner
from app.services.strategy_v2.instruments import infer_market, parse_instrument

from tests.test_strategy_v2_runtime import _frame


def test_coerce_int_from_complex_imaginary_suffix():
    assert coerce_param_value(7j, "int") == 7
    assert coerce_param_value("7j", "int") == 7
    assert coerce_param_value("2026j", "int") == 2026
    assert coerce_param_value(2026 + 0j, "int") == 2026
    assert coerce_param_value("7.0", "int") == 7
    assert coerce_param_value("2026-09-18", "int") == 2026


def test_round_after_merge_does_not_see_complex():
    source = """
# @param expiry_year int 2026 Expiry year
# @param min_entry_dte int 7 Min DTE
# @param max_entry_dte int 45 Max DTE
"""
    merged = merge_declared_params(
        source,
        {"expiry_year": "2026j", "min_entry_dte": 7j, "max_entry_dte": "45"},
    )
    assert int(round(merged["expiry_year"])) == 2026
    assert int(round(merged["min_entry_dte"])) == 7
    assert int(round(merged["max_entry_dte"])) == 45


def test_indicator_parser_casts_float_strings_and_imag_suffix():
    declared = IndicatorParamsParser.parse_params(
        "# @param expiry_year int 2026j year\n# @param min_entry_dte int 7.0 dte\n"
    )
    by_name = {item["name"]: item["default"] for item in declared}
    assert by_name["expiry_year"] == 2026
    assert by_name["min_entry_dte"] == 7


def test_parse_instrument_keeps_etf_option_code_not_chinese_name():
    spec = parse_instrument("CNIndexOptions:50ETF购9月2750 [10010971]")
    assert spec.market == "CNIndexOptions"
    assert spec.symbol == "10010971"
    assert spec.key == "CNIndexOptions:10010971"
    assert infer_market("10010971") == "CNIndexOptions"
    assert parse_instrument("10010971").key == "CNIndexOptions:10010971"


def test_backtest_reads_params_with_imag_suffix_and_trades_etf_option_code():
    code = """
# @param expiry_year int 2026 Expiry year
# @param min_entry_dte int 7 Min DTE
# @param max_entry_dte int 45 Max DTE

def initialize(context):
    context.set_universe(["CNIndexOptions:10010971"])
    context.subscribe(frequency="1d")

def handle_data(context, data):
    expiry_year = int(round(context.params.get("expiry_year", 2026)))
    min_dte = int(round(context.params.get("min_entry_dte", 7)))
    max_dte = int(round(context.params.get("max_entry_dte", 45)))
    if expiry_year < 2000 or min_dte < 0 or max_dte < min_dte:
        return
    if data.current("CNIndexOptions:10010971", "close") <= 0:
        return
    order("CNIndexOptions:50ETF购9月2750 [10010971]", 1)
"""
    runner = StrategyV2BacktestRunner(
        code=code,
        frames={"CNIndexOptions:10010971": _frame([0.08, 0.09, 0.07, 0.06])},
        initial_capital=100000,
        commission=0,
        slippage=0,
        params={"expiry_year": "2026j", "min_entry_dte": 7j, "max_entry_dte": "45"},
    )
    result = runner.run()
    symbols = {trade["symbol"] for trade in result["rawTrades"]}
    assert symbols == {"CNIndexOptions:10010971"}
    assert result["rawTrades"][0]["quantity"] == 1.0


def test_etf_option_percent_order_uses_contract_multiplier():
    code = """
def initialize(context):
    context.set_universe(["CNIndexOptions:10010971"])
    context.subscribe(frequency="1d")

def handle_data(context, data):
    if get_position("CNIndexOptions:10010971").amount == 0:
        order_target_percent("CNIndexOptions:10010971", 0.1)
"""
    runner = StrategyV2BacktestRunner(
        code=code,
        frames={"CNIndexOptions:10010971": _frame([0.10, 0.10, 0.10, 0.10])},
        initial_capital=100000,
        commission=0,
        slippage=0,
    )
    result = runner.run()
    qty = result["rawTrades"][0]["quantity"]
    assert qty == 10.0


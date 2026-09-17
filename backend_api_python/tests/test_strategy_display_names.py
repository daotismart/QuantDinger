from app.services.strategy_display_names import (
    compose_strategy_display_name,
    extract_code_doc_title,
    format_universe_symbol,
    is_auto_generated_strategy_name,
    variant_label_from_metadata,
)


def test_is_auto_generated_strategy_name():
    assert is_auto_generated_strategy_name("[AUTO-BT3]12-template_12-2026-06-01")
    assert is_auto_generated_strategy_name("[PR14-BT]template_None")
    assert not is_auto_generated_strategy_name("Quality Growth Multi-Factor")


def test_extract_code_doc_title():
    code = '"""\nQuality Growth Multi-Factor\nWeekly ranking.\n"""\n\ndef initialize(context):\n    pass\n'
    assert extract_code_doc_title(code) == "Quality Growth Multi-Factor"


def test_format_universe_symbol_for_cn_pack():
    label = format_universe_symbol(
        instruments=[
            {"market": "CNFutures", "symbol": "SA701"},
            {"market": "CNFuturesOptions", "symbol": "SA701-C-1000"},
        ]
    )
    assert label == "SA701 + SA701-C-1000"


def test_compose_strategy_display_name_replaces_auto_name():
    name = compose_strategy_display_name(
        name="[AUTO-BT3]11-template_11-2026-06-01",
        code='"""\nLow Volatility Rotation\n"""\n',
        template_title="Low Volatility Rotation",
    )
    assert name == "Low Volatility Rotation"


def test_compose_strategy_display_name_adds_variant_label():
    name = compose_strategy_display_name(
        name="Statistical Arbitrage Pack variant 3",
        template_title="Statistical Arbitrage Pack",
        params={"variant": 3},
        metadata={"variant_labels": ["A", "B", "C", "Spread Z", "E"]},
    )
    assert name == "Statistical Arbitrage Pack · Spread Z"


def test_variant_label_default():
    assert variant_label_from_metadata({}, 0) == "Variant 1"

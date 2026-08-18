"""CZCE 3-digit month codes must expand to Sina YYMM for history feeds."""

from __future__ import annotations

from datetime import datetime

from app.data_sources.cn_futures import resolve_history_symbol
from app.markets.cn_futures import (
    expand_cn_delivery_month,
    is_continuous_month,
    to_sina_contract_symbol,
)
from app.markets.cn_options import parse_cn_option_instrument, sina_option_symbol


def test_expand_czce_ymm_to_yymm():
    now = datetime(2026, 8, 17)
    assert is_continuous_month("")
    assert is_continuous_month("0")
    assert not is_continuous_month("701")
    assert expand_cn_delivery_month("701", exchange="CZCE", now=now) == "2701"
    assert expand_cn_delivery_month("509", exchange="CZCE", now=now) == "2509"
    assert expand_cn_delivery_month("2509", exchange="CZCE", now=now) == "2509"
    assert expand_cn_delivery_month("0", exchange="CZCE", now=now) == "0"
    assert expand_cn_delivery_month("2509", exchange="SHFE", now=now) == "2509"


def test_sina_symbols_go_through_one_mapper():
    now = datetime(2026, 8, 17)
    assert to_sina_contract_symbol("SA701", now=now) == "SA2701"
    assert to_sina_contract_symbol("sa701", now=now) == "SA2701"
    assert to_sina_contract_symbol("SA2701", now=now) == "SA2701"
    assert to_sina_contract_symbol("SA0", now=now) == "SA0"
    assert to_sina_contract_symbol("RB2509", now=now) == "RB2509"
    assert resolve_history_symbol("SA701") == ("SA2701", "contract")
    assert resolve_history_symbol("SA2701") == ("SA2701", "contract")
    assert resolve_history_symbol("SA0") == ("SA0", "continuous")
    assert resolve_history_symbol("TA509") == ("TA2509", "contract")


def test_czce_option_sina_code_uses_expanded_month():
    parsed = parse_cn_option_instrument("SA701C1800")
    assert parsed is not None
    assert sina_option_symbol(parsed) == "sa2701C1800"

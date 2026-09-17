"""Options desk: chain filters, combo greeks/margin, IV proxy, agent routes."""

from __future__ import annotations

from datetime import date

import pytest

from app.services.factors import compute_factor
from app.services.options_desk.chain import query_option_chain
from app.services.options_desk.combo import ComboError, estimate_combo, parse_combo_legs
from app.services.options_desk.greeks import black_scholes_greeks
from app.services.options_desk.iv_rank import iv_rank_from_closes
from app.services.strategy_v2.contract import StrategyV2ContractError, compile_strategy_v2
from app.utils import agent_auth


def _catalog():
    return [
        {
            "market": "CNIndexOptions",
            "symbol": "10010971",
            "name": "50ETF购9月2750",
            "exchange": "SSE",
            "kind": "etf",
            "underlying": "510050",
            "call_put": "C",
            "strike": 2.75,
            "expire_date": "2026-09-23",
            "lot_size": 10000,
        },
        {
            "market": "CNIndexOptions",
            "symbol": "10010972",
            "name": "50ETF沽9月2700",
            "exchange": "SSE",
            "kind": "etf",
            "underlying": "510050",
            "call_put": "P",
            "strike": 2.70,
            "expire_date": "2026-09-23",
            "lot_size": 10000,
        },
        {
            "market": "CNIndexOptions",
            "symbol": "10019999",
            "name": "300ETF购12月4000",
            "exchange": "SSE",
            "kind": "etf",
            "underlying": "510300",
            "call_put": "C",
            "strike": 4.0,
            "expire_date": "2026-12-23",
            "lot_size": 10000,
        },
    ]


def _token(scopes: str = "R,T") -> dict:
    return {
        "id": 42,
        "user_id": 1,
        "name": "options-desk",
        "scopes": scopes,
        "markets": "*",
        "instruments": "*",
        "paper_only": True,
        "rate_limit_per_min": 60,
        "status": "active",
        "expires_at": None,
    }


def test_black_scholes_atm_call_delta_near_half():
    greeks = black_scholes_greeks(
        spot=100.0,
        strike=100.0,
        tte=1.0,
        sigma=0.2,
        is_call=True,
        rate=0.0,
        dividend=0.0,
    )
    assert greeks["delta"] == pytest.approx(0.5398, abs=0.01)
    assert greeks["price"] > 0
    put = black_scholes_greeks(
        spot=100.0,
        strike=100.0,
        tte=1.0,
        sigma=0.2,
        is_call=False,
        rate=0.0,
        dividend=0.0,
    )
    assert put["delta"] == pytest.approx(greeks["delta"] - 1.0, abs=1e-9)


def test_chain_filters_by_underlying_dte_and_delta():
    as_of = date(2026, 8, 24)

    def kline_loader(**_kwargs):
        return [{"close": 2.80}] * 40

    payload = query_option_chain(
        underlying="510050",
        dte_min=20,
        dte_max=45,
        side="C",
        target_delta=0.5,
        catalog=_catalog(),
        kline_loader=kline_loader,
        as_of=as_of,
    )
    symbols = [row["symbol"] for row in payload["contracts"]]
    assert symbols == ["10010971"]
    assert payload["contracts"][0]["dte"] == 30
    assert payload["contracts"][0]["delta"] is not None


def test_parse_combo_legs_rejects_single_leg():
    with pytest.raises(ComboError) as caught:
        parse_combo_legs([{"symbol": "10010971", "side": "buy", "qty": 1}])
    assert caught.value.code == "combo.legCount"


def test_iron_condor_uses_defined_risk_width_margin():
    legs = parse_combo_legs(
        [
            {"symbol": "P1", "side": "buy", "qty": 1, "call_put": "P", "strike": 2.4},
            {"symbol": "P2", "side": "sell", "qty": 1, "call_put": "P", "strike": 2.5},
            {"symbol": "C1", "side": "sell", "qty": 1, "call_put": "C", "strike": 2.7},
            {"symbol": "C2", "side": "buy", "qty": 1, "call_put": "C", "strike": 2.8},
        ]
    )
    estimate = estimate_combo(legs, spot=2.6, sigma=0.2, dte=30)
    assert estimate["margin_method"] == "defined_risk_width"
    assert estimate["margin_estimate"] == pytest.approx(1000.0)
    assert estimate["conservative"] is True
    assert all(key in estimate["greeks"] for key in ("delta", "gamma", "vega", "theta"))


def test_iv_rank_and_percentile_from_realized_vol():
    import math
    import random

    rng = random.Random(7)
    closes = [100.0]
    for _ in range(80):
        closes.append(closes[-1] * math.exp(rng.gauss(0.0, 0.004)))
    for _ in range(50):
        closes.append(closes[-1] * math.exp(rng.gauss(0.0, 0.04)))
    payload = iv_rank_from_closes(closes, window=20, lookback=60)
    assert payload["proxy"] == "realized_vol"
    assert payload["iv_rank"] is not None
    assert 0 <= payload["iv_rank"] <= 100
    assert 0 <= payload["iv_percentile"] <= 100
    assert payload["iv_rank"] > 50
    assert payload["current_rv"] > payload["rv_low"]


def test_iv_rank_factor_computes_on_close_series():
    import numpy as np
    import pandas as pd

    index = np.arange(180, dtype=float)
    close = 100.0 + index * 0.05 + np.sin(index / 8.0)
    frame = pd.DataFrame({"close": close})
    rank = compute_factor("iv_rank", frame)
    percentile = compute_factor("iv_percentile", frame)
    assert 0 <= rank <= 100
    assert 0 <= percentile <= 100


def test_strategy_v2_order_combo_is_accepted():
    program = compile_strategy_v2(
        """
def initialize(context):
    context.set_universe(["CNIndexOptions:10010971"])
    context.subscribe(frequency="1d")

def handle_data(context, data):
    order_combo([
        {"symbol": "10010971", "side": "buy", "qty": 1},
        {"symbol": "10010972", "side": "sell", "qty": 1},
    ], reason="test_combo")
"""
    )
    assert program.handler("handle_data") is not None


def test_strategy_v2_order_combo_rejects_one_leg():
    with pytest.raises(StrategyV2ContractError, match="order_combo:legCount"):
        compile_strategy_v2(
            """
def initialize(context):
    context.set_universe(["CNIndexOptions:10010971"])
    context.subscribe(frequency="1d")

def handle_data(context, data):
    order_combo([{"symbol": "10010971", "side": "buy", "qty": 1}])
"""
        )


@pytest.fixture
def _agent_auth(monkeypatch):
    agent_auth._schema_ready = True
    agent_auth._rate_state.clear()
    monkeypatch.setattr(agent_auth, "_lookup_token", lambda _raw: _token())
    monkeypatch.setattr(agent_auth, "_touch_token_last_used", lambda *_: None)
    monkeypatch.setattr(agent_auth, "_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(agent_auth, "_reserve_idempotency", lambda *_: ("reserved", None))
    monkeypatch.setattr(agent_auth, "_complete_idempotency", lambda *_: None)
    yield
    agent_auth._rate_state.clear()


def test_agent_options_chain_route(client, monkeypatch, _agent_auth):
    monkeypatch.setattr(
        "app.routes.agent_v1.options.query_option_chain",
        lambda **kwargs: {"underlying": kwargs["underlying"], "contracts": [{"symbol": "10010971"}], "count": 1},
    )
    response = client.get(
        "/api/agent/v1/options/chain?underlying=510050&dte_min=20&target_delta=0.25",
        headers={"Authorization": "Bearer qd_agent_TESTTOKEN12345"},
    )
    assert response.status_code == 200
    assert response.get_json()["data"]["contracts"][0]["symbol"] == "10010971"


def test_agent_combo_estimate_and_paper_order(client, monkeypatch, _agent_auth):
    monkeypatch.setattr("app.routes.agent_v1.options.catalog_by_symbol", lambda _symbols, **_k: {})
    monkeypatch.setattr("app.routes.agent_v1.options._last_price", lambda *_a, **_k: 0.05)
    monkeypatch.setattr(
        "app.routes.agent_v1.options._record_paper_combo",
        lambda legs, combo_uid, fills: [
            {
                "order_uid": f"p{item['index']}",
                "leg_index": item["index"],
                "symbol": item["symbol"],
                "side": item["side"],
                "qty": item["qty"],
                "fill_price": 0.05,
                "status": "filled",
                "paper": True,
            }
            for item in legs
        ],
    )
    monkeypatch.setattr("app.routes.agent_v1.options.record_completed_job", lambda **_k: None)
    headers = {
        "Authorization": "Bearer qd_agent_TESTTOKEN12345",
        "Idempotency-Key": "combo-test-1",
    }
    legs = [
        {"symbol": "10010971", "side": "buy", "qty": 1, "call_put": "C", "strike": 2.75},
        {"symbol": "10010980", "side": "sell", "qty": 1, "call_put": "C", "strike": 2.85},
        {"symbol": "10010990", "side": "sell", "qty": 1, "call_put": "P", "strike": 2.55},
        {"symbol": "10010991", "side": "buy", "qty": 1, "call_put": "P", "strike": 2.45},
    ]
    estimate = client.post(
        "/api/agent/v1/options/combo/estimate",
        headers=headers,
        json={"legs": legs, "spot": 2.65, "sigma": 0.2, "dte": 30},
    )
    assert estimate.status_code == 200
    body = estimate.get_json()["data"]
    assert body["margin_method"] == "defined_risk_width"
    assert body["conservative"] is True

    order = client.post(
        "/api/agent/v1/options/combo/order",
        headers=headers,
        json={"legs": legs, "spot": 2.65},
    )
    assert order.status_code == 200
    payload = order.get_json()["data"]
    assert payload["atomic"] is True
    assert payload["paper"] is True
    assert len(payload["legs"]) == 4


def test_etf_options_ingest_task_skips_when_disabled(monkeypatch):
    monkeypatch.setenv("CN_ETF_OPTIONS_INGEST_ENABLED", "false")
    from app.tasks.maintenance import run_cn_etf_options_history_ingest

    result = run_cn_etf_options_history_ingest.__wrapped__()
    assert result["skipped"] is True

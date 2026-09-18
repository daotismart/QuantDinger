"""ETF options: multi-month selection helpers for stacked GEX charts."""

from app.services.cn_derivatives_etf import _aggregate_etf_chains_by_strike


def test_aggregate_etf_chains_by_strike_sums_oi_and_weights_mids():
    chains = [
        [
            {"strike": 3.0, "call_oi": 10, "put_oi": 4, "call_mid": 0.1, "put_mid": 0.2},
            {"strike": 3.1, "call_oi": 1, "put_oi": 2, "call_mid": 0.05, "put_mid": 0.08},
        ],
        [
            {"strike": 3.0, "call_oi": 5, "put_oi": 6, "call_mid": 0.2, "put_mid": 0.1},
        ],
    ]
    rows = _aggregate_etf_chains_by_strike(chains)
    by_k = {r["strike"]: r for r in rows}
    assert by_k[3.0]["call_oi"] == 15
    assert by_k[3.0]["put_oi"] == 10
    assert abs(by_k[3.0]["call_mid"] - (0.1 * 10 + 0.2 * 5) / 15) < 1e-9
    assert by_k[3.1]["call_oi"] == 1
    assert by_k[3.1]["put_oi"] == 2


def test_select_all_month_cap_is_eight():
    """Source guard: '全部' must request more than the old 2-month slice."""
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "app" / "services" / "cn_derivatives_etf.py"
    text = src.read_text(encoding="utf-8")
    assert "months[:8] if select_all" in text
    assert "months[:2] if select_all" not in text

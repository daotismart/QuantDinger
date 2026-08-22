"""ETF composite page product picker catalogs."""

from app.services.cn_derivatives_etf import list_etf_derivative_products


def test_index_tab_includes_futures_and_spot_indices():
    rows = list_etf_derivative_products("index")
    roots = {r["root"] for r in rows}
    kinds = {r.get("picker_kind") for r in rows}
    assert "IF" in roots
    assert "000300.SH" in roots
    assert "index_futures" in kinds
    assert "spot_index" in kinds


def test_etf_tab_uses_full_cn_symbols_and_us_hk():
    rows = list_etf_derivative_products("etf")
    cn = [r for r in rows if r.get("picker_kind") == "cn_etf"]
    assert any(r["root"] == "510050.SH" for r in cn)
    assert any(r.get("market") == "USStock" for r in rows)
    assert any(r.get("market") == "HKStock" for r in rows)


def test_etf_options_tab_uses_underlying_codes_with_cn_names():
    rows = list_etf_derivative_products("etfOptions")
    assert rows
    first = rows[0]
    assert first.get("picker_kind") == "etf_options"
    assert len(str(first.get("root") or "")) == 6
    assert "510050" in str(first.get("stock_symbol") or "")

"""ETF composite page shared product picker catalogs."""

from app.services.cn_derivatives_etf import list_etf_derivative_products


def test_products_are_cn_etf_only_regardless_of_tab():
    for tab in ("index", "etf", "etfOptions", ""):
        rows = list_etf_derivative_products(tab)
        assert rows
        assert all(r.get("picker_kind") == "cn_etf" for r in rows)
        assert all(r.get("market") == "CNStock" for r in rows)
        assert not any(r.get("picker_kind") in {"index_futures", "spot_index", "us_hk_etf"} for r in rows)
        assert not any(r.get("market") in {"USStock", "HKStock", "CNIndexFutures"} for r in rows)


def test_products_include_benchmark_index_and_options_flags():
    rows = list_etf_derivative_products("etf")
    by_code = {r.get("underlying_code"): r for r in rows}
    assert "510050" in by_code
    row = by_code["510050"]
    assert row["root"] == "510050.SH"
    assert row["has_options"] is True
    assert row["index_symbol"] == "000016.SH"
    assert row["index_name"]
    assert row["index_futures_root"] == "IH"


def test_star50_and_chinext_have_index_without_futures():
    rows = {r["underlying_code"]: r for r in list_etf_derivative_products()}
    assert rows["588000"]["index_symbol"] == "000688.SH"
    assert rows["588000"]["index_futures_root"] == ""
    assert rows["159915"]["index_symbol"] == "399006.SZ"
    assert rows["159915"]["index_futures_root"] == ""

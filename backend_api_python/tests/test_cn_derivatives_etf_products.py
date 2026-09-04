"""ETF composite page shared product picker catalogs."""

import time

from app.services import cn_derivatives_etf as etf_mod
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


def test_etf_spot_panel_uses_local_bars_when_sina_hangs(monkeypatch):
    def _bars(symbol):
        if symbol == "510050.SH":
            return [{"time": 1756800000, "close": 2.881, "volume": 12345}]
        if symbol == "000016.SH":
            return [{"time": 1756800000, "close": 2712.5, "volume": 1}]
        return []

    def _hang(*_args, **_kwargs):
        time.sleep(8)
        raise RuntimeError("sina should not be awaited")

    monkeypatch.setattr(etf_mod, "_SINA_TIMEOUT_SEC", 0.2)
    monkeypatch.setattr(etf_mod, "_ENRICH_TIMEOUT_SEC", 0.2)
    monkeypatch.setattr(etf_mod, "_query_local_daily_bars", _bars)
    monkeypatch.setattr(etf_mod, "_load_etf_spot_frame_sina", _hang)
    monkeypatch.setattr(
        "app.services.cn_derivatives_analytics._ak",
        lambda: type("AK", (), {"stock_zh_index_spot_sina": staticmethod(_hang)})(),
    )
    monkeypatch.setattr(
        "app.services.cn_derivatives_etf_metrics.enrich_etf_metrics",
        lambda code, row=None: dict(row or {}),
    )
    monkeypatch.setattr(
        etf_mod,
        "_etf_product_payload",
        lambda code6: {"root": code6, "name_cn": "上证50ETF", "underlying_code": code6},
    )

    started = time.monotonic()
    panel = etf_mod.build_etf_spot_panel("510050.SH")
    elapsed = time.monotonic() - started
    assert elapsed < 3.0
    assert panel["spot_price"] == 2.881
    assert panel["spot"]["etf"]["price"] == 2.881
    assert panel["spot"]["etf"]["source"] == "qd_market_bars"
    assert panel["spot"]["index"]["price"] == 2712.5
    assert "2.8810" in "".join(panel["analysis"])


def test_spot_index_panel_uses_local_bars_when_sina_hangs(monkeypatch):
    monkeypatch.setattr(etf_mod, "_SINA_TIMEOUT_SEC", 0.2)
    monkeypatch.setattr(
        etf_mod,
        "_query_local_daily_bars",
        lambda symbol: [{"time": 1, "close": 3999.1, "volume": 10}],
    )
    monkeypatch.setattr(
        "app.services.cn_derivatives_analytics._ak",
        lambda: type("AK", (), {"stock_zh_index_spot_sina": staticmethod(lambda: time.sleep(8))})(),
    )
    started = time.monotonic()
    panel = etf_mod.build_spot_index_panel("000016.SH")
    assert time.monotonic() - started < 2.5
    assert panel["spot_price"] == 3999.1


def test_products_are_static_and_skip_ctp_catalog(monkeypatch):
    def _boom(*_args, **_kwargs):
        raise AssertionError("live CTP option catalog should not be scanned")

    monkeypatch.setattr(
        "app.services.cn_options_chain.listed_etf_underlying_catalog",
        _boom,
    )
    monkeypatch.setattr(
        "app.services.cn_options_chain.listed_option_catalog",
        _boom,
    )
    from app.markets.cn_options import KNOWN_ETF_UNDERLYINGS

    started = time.monotonic()
    rows = list_etf_derivative_products("etf")
    assert time.monotonic() - started < 0.5
    codes = {r["underlying_code"] for r in rows}
    assert codes == set(KNOWN_ETF_UNDERLYINGS)
    assert "510050" in codes
    assert len(rows) == 9


def test_etf_product_payload_skips_live_catalog(monkeypatch):
    def _boom(*_args, **_kwargs):
        raise AssertionError("live option catalog should not be scanned")

    monkeypatch.setattr(etf_mod, "list_etf_derivative_products", _boom)
    row = etf_mod._etf_product_payload("510050")
    assert row["root"] == "510050.SH"
    assert row["underlying_code"] == "510050"
    assert row["index_symbol"] == "000016.SH"
    assert row["picker_kind"] == "cn_etf"

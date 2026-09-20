"""ETF composite page shared product picker catalogs."""

import time

import pytest

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


def test_etf_spot_panel_enriches_when_local_price_exists(monkeypatch):
    called = {}

    def _enrich(code, row=None):
        called["code"] = code
        out = dict(row or {})
        out.update(
            {
                "total_fee_pct": 0.2,
                "constituent_profit_sum": 1.2e12,
                "avg_pe": 12.5,
                "holdings_count": 50,
                "holdings": [{"code": "600000", "name": "浦发银行", "weight_pct": 3.1}],
                "amount": 1.4e9,
                "scale": 2.3e10,
            }
        )
        return out

    monkeypatch.setattr(etf_mod, "_SINA_TIMEOUT_SEC", 0.2)
    monkeypatch.setattr(etf_mod, "_ENRICH_TIMEOUT_SEC", 2.0)
    monkeypatch.setattr(
        etf_mod,
        "_query_local_daily_bars",
        lambda symbol: (
            [{"time": 1756800000, "close": 2.881, "volume": 12345}]
            if symbol in {"510050.SH", "000016.SH"}
            else []
        ),
    )
    monkeypatch.setattr(
        "app.services.cn_derivatives_etf_metrics.enrich_etf_metrics",
        _enrich,
    )
    monkeypatch.setattr(
        etf_mod,
        "_etf_product_payload",
        lambda code6: {"root": code6, "name_cn": "上证50ETF", "underlying_code": code6},
    )
    monkeypatch.setattr(
        etf_mod,
        "_load_etf_spot_frame_sina",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("sina should be skipped")),
    )

    panel = etf_mod.build_etf_spot_panel("510050.SH")
    assert called.get("code") == "510050"
    etf = panel["spot"]["etf"]
    assert etf["price"] == 2.881
    assert etf["total_fee_pct"] == 0.2
    assert etf["avg_pe"] == 12.5
    assert etf["scale"] == 2.3e10
    assert etf["holdings_count"] == 50


def test_etf_spot_panel_uses_local_bars_when_sina_hangs(monkeypatch):
    def _hang(*_args, **_kwargs):
        time.sleep(8)
        raise RuntimeError("sina should not be awaited")

    monkeypatch.setattr(etf_mod, "_SINA_TIMEOUT_SEC", 0.2)
    monkeypatch.setattr(etf_mod, "_ENRICH_TIMEOUT_SEC", 0.2)
    monkeypatch.setattr(
        etf_mod,
        "_query_local_daily_bars",
        lambda symbol: (
            [{"time": 1756800000, "close": 2.881, "volume": 12345}]
            if symbol in {"510050.SH", "000016.SH"}
            else []
        ),
    )
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
    assert time.monotonic() - started < 3.0
    assert panel["spot_price"] == 2.881
    assert panel["spot"]["etf"]["source"] == "qd_market_bars"


def test_linked_etf_codes_for_index():
    assert etf_mod.linked_etf_codes_for_index("000016.SH") == ["510050"]
    assert "510300" in etf_mod.linked_etf_codes_for_index("000300.SH")
    assert etf_mod.linked_etf_codes_for_index("399006.SZ") == ["159915"]
    assert etf_mod._resolve_linked_etf_code("000688.SH", "588080") == "588080"
    assert etf_mod._resolve_linked_etf_code("000688.SH", "") == "588000"


def test_spot_index_panel_attaches_index_analysis(monkeypatch):
    monkeypatch.setattr(
        etf_mod,
        "_index_row_from_local_bars",
        lambda symbol: {"code": symbol, "name": "上证50指数", "price": 2860.77, "volume": 123},
    )
    monkeypatch.setattr(etf_mod, "_ENRICH_TIMEOUT_SEC", 2.0)
    monkeypatch.setattr(
        "app.services.cn_derivatives_etf_metrics.load_index_activity",
        lambda symbol, local_volume=None: {
            "volume": 39360945.0,
            "volume_unit": "手",
            "volume_shares": 3936094500.0,
            "amount": 138366086012.0,
            "amount_unit": "元",
            "checks": [{"field": "volume", "status": "match"}],
            "checked": True,
            "note": "校对通过：本地日线与腾讯/新浪一致。",
        },
    )
    monkeypatch.setattr(
        "app.services.cn_derivatives_etf_metrics.build_index_etf_shares",
        lambda codes, index_market_cap=None, primary="": {
            "etfs": [
                {
                    "code": "510050",
                    "name": "上证50ETF",
                    "scale": 2.32e10,
                    "share_pct": 0.2578,
                    "etf_group_share_pct": 100.0,
                    "primary": True,
                }
            ],
            "primary": "510050",
            "total_scale": 2.32e10,
            "index_market_cap": 9e12,
            "combined_share_pct": 0.2578,
        },
    )
    option_panel = {
        "greeks": {"delta": 1e7, "gamma": 2e5, "vega": 3e6, "theta": -4e5},
        "underlying": 2.97,
        "gex_summary": {"net_gex": 5.94e5},
        "multiplier": 10000,
        "capital_curve": {
            "total": {
                "premium_total": 1.2e8,
                "margin_total": 4.5e8,
                "margin_short_total": 4.5e8,
                "time_value_total": 3.3e7,
            }
        },
    }
    monkeypatch.setattr(
        etf_mod,
        "_etf_options_cache_get",
        lambda key: option_panel if key.endswith(":510050:all") else None,
    )
    monkeypatch.setattr(
        etf_mod,
        "build_etf_options_panel",
        lambda code, month=None: (_ for _ in ()).throw(AssertionError("live option rebuild")),
    )
    monkeypatch.setattr(
        "app.services.cn_derivatives_etf_metrics.enrich_index_metrics",
        lambda symbol, live=False: {
            "holdings_count": 50,
            "avg_pe": 12.5,
            "avg_profit_margin": 16.2,
            "constituent_market_cap_sum": 9e12,
            "constituent_profit_sum": 1.2e12,
            "constituent_profit_coverage": 50,
            "market_cap_coverage": 50,
            "pe_coverage": 49,
            "margin_coverage": 50,
            "holdings": [{"code": "600519", "name": "贵州茅台", "weight_pct": 8.5, "pe_ratio": 19.3}],
        },
    )
    panel = etf_mod.build_spot_index_panel("000016.SH")
    assert panel["spot_price"] == 2860.77
    assert "etf" not in (panel.get("spot") or {})
    idx = panel["spot"]["index"]
    assert idx["avg_pe"] == 12.5
    assert idx["holdings_count"] == 50
    assert idx["holdings"][0]["code"] == "600519"
    assert idx["volume"] == 39360945.0
    assert idx["amount"] == 138366086012.0
    assert idx["volume_unit"] == "手"
    assert idx["linked_etfs"][0]["code"] == "510050"
    assert idx["etf_share"]["combined_share_pct"] == 0.2578
    assert idx["option_greeks"]["delta_notional"] == pytest.approx(1e7 * 2.97)
    assert idx["option_greeks"]["gamma_notional"] == 5.94e5
    assert idx["option_greeks"]["premium_total"] == 1.2e8
    assert idx["option_greeks"]["margin_total"] == 4.5e8
    assert idx["option_greeks"]["time_value_total"] == 3.3e7
    assert idx["option_greeks"]["etfs"][0]["etf_code"] == "510050"
    text = "".join(panel["analysis"])
    assert "上证50指数" in text
    assert "12.50" in text
    assert "成交额" in text
    assert "手" in text
    assert "校对通过" in text
    assert "占指数成份市值" in text
    assert "Delta 名义资金" in text
    assert "权利金" in text
    assert "保证金" in text
    assert "时间价值" in text
    assert "运作费率" not in text


def test_spot_index_panel_skips_live_option_rebuild_on_cache_miss(monkeypatch):
    monkeypatch.setattr(
        etf_mod,
        "_index_row_from_local_bars",
        lambda symbol: {"code": symbol, "name": "上证50指数", "price": 2860.77, "volume": 123},
    )
    monkeypatch.setattr(etf_mod, "_ENRICH_TIMEOUT_SEC", 2.0)
    monkeypatch.setattr(
        "app.services.cn_derivatives_etf_metrics.load_index_activity",
        lambda symbol, local_volume=None: {
            "volume": 39360945.0,
            "volume_unit": "手",
            "amount": 138366086012.0,
        },
    )
    monkeypatch.setattr(
        "app.services.cn_derivatives_etf_metrics.build_index_etf_shares",
        lambda codes, index_market_cap=None, primary="": {
            "etfs": [{"code": "510050", "name": "上证50ETF", "scale": 2.32e10, "share_pct": 0.2578, "primary": True}],
            "primary": "510050",
            "total_scale": 2.32e10,
            "index_market_cap": 9e12,
            "combined_share_pct": 0.2578,
        },
    )
    monkeypatch.setattr(etf_mod, "_etf_options_cache_get", lambda key: None)
    monkeypatch.setattr(
        etf_mod,
        "build_etf_options_panel",
        lambda code, month=None: (_ for _ in ()).throw(AssertionError("live option rebuild")),
    )
    monkeypatch.setattr(
        "app.services.cn_derivatives_etf_metrics.enrich_index_metrics",
        lambda symbol, live=False: {
            "holdings_count": 50,
            "avg_pe": 12.5,
            "constituent_market_cap_sum": 9e12,
            "holdings": [{"code": "600519", "name": "贵州茅台"}],
        },
    )
    started = time.monotonic()
    panel = etf_mod.build_spot_index_panel("000016.SH", etf_code="510050")
    assert time.monotonic() - started < 2.0
    idx = panel["spot"]["index"]
    assert idx["price"] == 2860.77
    assert idx["volume"] == 39360945.0
    assert idx["amount"] == 138366086012.0
    assert idx["holdings_count"] == 50
    assert idx["avg_pe"] == 12.5
    assert idx["etf_share"]["combined_share_pct"] == 0.2578
    assert idx["option_greeks"].get("delta_notional") is None
    assert idx["option_greeks"].get("etfs") == []
    assert "Delta 名义资金" not in "".join(panel["analysis"])

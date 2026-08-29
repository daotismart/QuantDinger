"""Tests for ETF constituent prefetch + durable fundamental store wiring."""

from __future__ import annotations

import app.services.cn_etf_constituent_prefetch as prefetch
import app.services.cn_etf_constituent_store as store
import app.services.cn_derivatives_etf_metrics as metrics


def test_list_etf_option_underlyings_includes_known(monkeypatch):
    import app.markets.cn_options as cn_options
    import app.services.cn_options_chain as chain

    monkeypatch.setattr(
        cn_options,
        "KNOWN_ETF_UNDERLYINGS",
        {"510300": "CSI 300 ETF", "510050": "SSE 50 ETF"},
    )
    monkeypatch.setattr(chain, "listed_etf_underlying_codes", lambda: ["510300", "159915"])
    out = prefetch.list_etf_option_underlyings(include_listed=True)
    assert "510300" in out
    assert "510050" in out
    assert "159915" in out


def test_collect_constituent_universe_uses_index_rows(monkeypatch):
    monkeypatch.setattr(
        metrics,
        "_load_constituent_base_rows",
        lambda code: (
            [
                {"code": "600519", "name": "Kweichow Moutai", "weight_pct": 5.0},
                {"code": "000858", "name": "Wuliangye", "weight_pct": 3.0},
            ],
            "index_stock_cons_weight_csindex",
            "000300 index 2026-07-31",
        ),
    )
    monkeypatch.setattr(metrics, "_benchmark_index_code", lambda code: "000300")
    universe = prefetch.collect_constituent_universe(["510300"])
    assert universe["constituent_count"] == 2
    assert universe["index_codes"] == ["000300"]
    assert set(universe["constituent_codes"]) == {"600519", "000858"}
    assert universe["by_etf"]["510300"]["source"] == "index_stock_cons_weight_csindex"


def test_warm_constituent_snapshots_rehydrates_from_db(monkeypatch):
    calls = {"snapshot": 0}

    monkeypatch.setattr(metrics, "_cache_get", lambda key: None)
    monkeypatch.setattr(metrics, "_cache_set", lambda *a, **k: None)
    monkeypatch.setattr(store, "ensure_schema", lambda: None)
    monkeypatch.setattr(
        store,
        "load_snapshots",
        lambda codes: {
            "600519": {
                "net_profit": 100.0,
                "pe_ratio": 20.0,
                "market_cap": 1e12,
                "profit_margin": 30.0,
            }
        },
    )

    def _snap(code):
        calls["snapshot"] += 1
        return {"net_profit": 1.0, "pe_ratio": 10.0}

    monkeypatch.setattr(metrics, "_stock_constituent_snapshot", _snap)
    monkeypatch.setattr(store, "upsert_snapshot", lambda *a, **k: None)

    stats = prefetch.warm_constituent_snapshots(["600519", "000858"], persist=True, force=False)
    assert stats["cached"] == 1
    assert stats["pending"] == 1
    assert stats["warmed"] == 1
    assert calls["snapshot"] == 1


def test_stock_constituent_snapshot_uses_db_before_network(monkeypatch):
    monkeypatch.setattr(metrics, "_cache_get", lambda key: None)
    sets = {}

    def _set(key, value, ttl=None):
        sets[key] = value

    monkeypatch.setattr(metrics, "_cache_set", _set)
    monkeypatch.setattr(
        store,
        "load_snapshot",
        lambda code, max_age_hours=72: {
            "net_profit": 88.0,
            "pe_ratio": 12.5,
            "market_cap": 9e11,
            "profit_margin": 18.0,
            "source": "db",
        },
    )

    # Network helpers should not be required when DB hit succeeds.
    monkeypatch.setattr(
        metrics,
        "_latest_net_profit",
        lambda code: (_ for _ in ()).throw(AssertionError("network should not run")),
    )

    out = metrics._stock_constituent_snapshot("600519")
    assert out["net_profit"] == 88.0
    assert out["pe_ratio"] == 12.5
    assert sets.get("etf:constituent_snapshot:600519")["net_profit"] == 88.0


def test_run_prefetch_cycle_orchestration(monkeypatch):
    monkeypatch.setattr(
        prefetch,
        "collect_constituent_universe",
        lambda etf_codes=None: {
            "etf_codes": ["510300"],
            "index_codes": ["000300"],
            "constituent_codes": ["600519"],
            "constituent_count": 1,
            "by_etf": {
                "510300": {"names": {"600519": "Kweichow Moutai"}},
            },
        },
    )
    monkeypatch.setattr(
        prefetch,
        "warm_constituent_snapshots",
        lambda *a, **k: {"total": 1, "warmed": 1, "cached": 0, "failed": 0, "persisted": 1},
    )
    monkeypatch.setattr(prefetch, "register_constituent_history_watch", lambda codes: 1)
    monkeypatch.setattr(
        prefetch,
        "warm_etf_metric_bundles",
        lambda *a, **k: {"ok": 1, "failed": 0, "skipped": 0, "details": []},
    )

    result = prefetch.run_etf_constituent_prefetch_cycle(
        force=True,
        include_history=True,
        warm_bundles=True,
        trigger="test",
    )
    assert result["etf_count"] == 1
    assert result["constituent_count"] == 1
    assert result["history_watch_written"] == 1
    assert result["snapshots"]["warmed"] == 1
    assert result["bundles"]["ok"] == 1

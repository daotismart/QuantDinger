"""CN futures/options discovery for watchlist search and market type pickers."""

from app.markets.registry import list_market_modules
from app.routes.settings import CONFIG_SCHEMA
from app.services.market import symbol_search
from app.utils.market_visibility import is_market_visible


def test_market_types_include_cn_futures_when_visible(client, monkeypatch):
    monkeypatch.setenv(
        "ENABLED_MARKETS",
        "USStock,CNFutures,CNIndexFutures,Futures",
    )
    resp = client.get("/api/market/types")
    assert resp.status_code == 200
    payload = resp.get_json()
    values = [row["value"] for row in payload["data"]]
    assert values == ["USStock", "CNFutures", "CNIndexFutures", "Futures"]


def test_cn_futures_visible_by_default(monkeypatch):
    monkeypatch.delenv("ENABLED_MARKETS", raising=False)
    monkeypatch.delenv("SHOW_CN_FUTURES", raising=False)
    monkeypatch.delenv("SHOW_CN_INDEX_DERIVATIVES", raising=False)
    assert is_market_visible("CNFutures") is True
    assert is_market_visible("CNFuturesOptions") is True
    assert is_market_visible("CNIndexFutures") is True
    assert is_market_visible("CNIndexOptions") is True


def test_cn_futures_hidden_when_flag_off(monkeypatch):
    monkeypatch.delenv("ENABLED_MARKETS", raising=False)
    monkeypatch.setenv("SHOW_CN_FUTURES", "false")
    assert is_market_visible("CNFutures") is False
    assert is_market_visible("CNStock") is False


def test_market_modules_settings_expose_cn_futures_toggle():
    items = {item["key"]: item for item in CONFIG_SCHEMA["market_modules"]["items"]}
    assert "ENABLED_MARKETS" in items
    assert items["SHOW_CN_FUTURES"]["default"] == "True"
    option_values = {opt["value"] for opt in items["ENABLED_MARKETS"]["options"]}
    assert {"CNFutures", "CNFuturesOptions", "CNIndexFutures", "CNIndexOptions"} <= option_values


def test_list_market_modules_marks_cn_futures_ready_when_enabled():
    rows = {
        item["key"]: item
        for item in list_market_modules({"SHOW_CN_FUTURES": "true"})
    }
    assert rows["CNFutures"]["enabled"] is True
    assert rows["CNFuturesOptions"]["enabled"] is True
    assert rows["CNFutures"]["status"] in {"ready", "partial"}


def test_find_cn_futures_contract_and_root():
    row = symbol_search.find_market_symbol("CNFutures", "rb2510")
    assert row is not None
    assert row["market"] == "CNFutures"
    assert row["symbol"] == "RB2510"
    assert row["settle_currency"] == "CNY"

    root = symbol_search.find_market_symbol("CNFutures", "RB")
    assert root is not None
    assert root["symbol"] == "RB"


def test_find_cn_index_futures_accepted_under_parent_market():
    row = symbol_search.find_market_symbol("CNFutures", "IF2509")
    assert row is not None
    assert row["symbol"] == "IF2509"

    indexed = symbol_search.find_market_symbol("CNIndexFutures", "IF2509")
    assert indexed is not None
    assert indexed["market"] == "CNIndexFutures"


def test_search_and_hot_cn_futures():
    rows = symbol_search.search_market_symbols("CNFutures", "rb", limit=10)
    assert rows
    assert any(r["symbol"].startswith("RB") for r in rows)

    hot = symbol_search.get_hot_symbols("CNFutures", limit=5)
    assert hot
    assert all(r["market"] == "CNFutures" for r in hot)

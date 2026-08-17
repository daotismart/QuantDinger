"""CN futures/options discovery for watchlist search and market type pickers."""

from app.services.market import symbol_search


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

"""Symbol hot/search filters for ETF derivatives composite page."""

from app.data.market_symbols_seed import get_hot_symbols as seed_get_hot_symbols
from app.services.market import symbol_search


def test_cnstock_hot_filters_by_asset_class(monkeypatch):
    rows = [
        {
            "market": "CNStock",
            "symbol": "000300.SH",
            "name": "CSI 300 Index",
            "exchange": "CN",
            "market_type": "index",
            "instrument_id": "",
            "settle_currency": "CNY",
            "currency": "CNY",
            "asset_class": "index",
        },
        {
            "market": "CNStock",
            "symbol": "510050.SH",
            "name": "SSE 50 ETF",
            "exchange": "CN",
            "market_type": "spot",
            "instrument_id": "",
            "settle_currency": "CNY",
            "currency": "CNY",
            "asset_class": "etf",
        },
    ]

    def _fake_hot(market, limit=10, *, asset_class="", etf_only=False):
        out = rows
        if asset_class:
            out = [r for r in out if r["asset_class"] == asset_class]
        return out[:limit]

    monkeypatch.setattr(symbol_search, "seed_get_hot_symbols", _fake_hot)

    index_hot = symbol_search.get_hot_symbols("CNStock", 10, asset_class="index")
    assert index_hot
    assert all(r["asset_class"] == "index" for r in index_hot)
    assert "510050.SH" not in {r["symbol"] for r in index_hot}

    etf_hot = symbol_search.get_hot_symbols("CNStock", 10, asset_class="etf")
    assert etf_hot
    assert all(r["asset_class"] == "etf" for r in etf_hot)
    assert "000300.SH" not in {r["symbol"] for r in etf_hot}


def test_cnstock_search_asset_class_not_crypto(monkeypatch):
    def _fake_search(market, keyword, limit=20, *, asset_class="", etf_only=False):
        return [
            {
                "market": "CNStock",
                "symbol": "510050.SH",
                "name": "SSE 50 ETF",
                "exchange": "CN",
                "market_type": "spot",
                "instrument_id": "",
                "settle_currency": "CNY",
                "asset_class": "etf",
            }
        ]

    monkeypatch.setattr(symbol_search, "seed_search_symbols", _fake_search)

    rows = symbol_search.search_market_symbols("CNStock", "510050", limit=5, asset_class="etf")
    assert rows
    assert rows[0]["asset_class"] == "etf"


def test_cnindexoptions_etf_only_skips_io_root(monkeypatch):
    monkeypatch.setattr(
        symbol_search,
        "seed_search_symbols",
        lambda market, keyword, limit=20, *, asset_class="", etf_only=False: [
            {
                "market": "CNIndexOptions",
                "symbol": "10010971",
                "name": "50ETF option",
                "exchange": "SSE",
                "market_type": "options",
                "instrument_id": "10010971",
                "settle_currency": "CNY",
                "asset_class": "options",
            }
        ],
    )

    rows = symbol_search.search_market_symbols("CNIndexOptions", "IO", limit=5, etf_only=True)
    assert rows
    assert rows[0]["symbol"] == "10010971"
    assert all(r["symbol"] != "IO" for r in rows)


def test_seed_get_hot_symbols_accepts_asset_class_filter(monkeypatch):
    captured = {}

    class _Cursor:
        def execute(self, sql, params):
            captured["sql"] = sql
            captured["params"] = params

        def fetchall(self):
            return []

        def close(self):
            return None

    class _Db:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def cursor(self):
            return _Cursor()

    monkeypatch.setattr(
        "app.data.market_symbols_seed._get_db_connection",
        lambda: _Db(),
    )

    seed_get_hot_symbols("CNStock", 5, asset_class="index")
    assert "asset_class = ?" in captured["sql"]
    assert "index" in captured["params"]

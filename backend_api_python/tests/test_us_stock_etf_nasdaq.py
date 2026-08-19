from datetime import datetime
from unittest.mock import MagicMock, patch

from app.data_sources.us_stock import USStockDataSource


def test_nasdaq_asset_class_prefers_etf_for_spy():
    assert USStockDataSource._nasdaq_asset_classes("SPY") == ("etf", "stocks")
    assert USStockDataSource._nasdaq_asset_classes("AAPL") == ("stocks", "etf")


@patch("app.data_sources.us_stock.requests.get")
def test_nasdaq_historical_uses_etf_assetclass_for_spy(mock_get):
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "data": {
            "tradesTable": {
                "rows": [
                    {
                        "date": "08/18/2026",
                        "open": "640.10",
                        "high": "642.00",
                        "low": "638.50",
                        "close": "641.20",
                        "volume": "1000000",
                    }
                ]
            }
        }
    }
    mock_get.return_value = mock_resp

    ds = USStockDataSource()
    bars = ds._fetch_nasdaq_historical(
        "SPY",
        datetime(2026, 6, 1),
        datetime(2026, 8, 18),
        100,
    )

    assert len(bars) == 1
    assert mock_get.call_args.kwargs["params"]["assetclass"] == "etf"

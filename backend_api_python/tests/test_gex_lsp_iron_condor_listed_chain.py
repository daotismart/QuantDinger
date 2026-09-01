"""Listed-chain iron-condor: display-name metadata, V2 intercept, no hardcoded legs."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from app.services.gex_lsp_strangle.chain_store import (
    complete_chain_metadata,
    fourth_wednesday,
    parse_etf_option_display_name,
)
from app.services.gex_lsp_strangle.iron_condor_engine import (
    IronCondorBacktestConfig,
    run_iron_condor_backtest,
)
from app.services.gex_lsp_strangle.v2_adapter import (
    config_from_params,
    research_to_v2_result,
    run_listed_chain_iron_condor,
)
from app.services.strategy_v2.service import StrategyV2BacktestService
from app.services.strategy_v2.snapshot import MarketDataSnapshotStore

REPO_ROOT = Path(__file__).resolve().parents[2]
CSV_DIR = REPO_ROOT / "tmp" / "gex_lsp_strangle"


class _Repository:
    def persist_run(self, **kwargs):
        self.persisted = kwargs
        return 991


def _synthetic_panel():
    dates = pd.date_range("2026-04-01", periods=30, freq="B")
    und = pd.DataFrame(
        {
            "trade_date": dates,
            "underlying_code": "510050",
            "open": 2.95,
            "high": 2.97,
            "low": 2.93,
            "close": 2.95,
            "volume": 8_000_000,
            "amount": 24_000_000,
        }
    )
    # Dense 0.05 grid so 3-step GEX-TV wings exist; ~56 DTE to 2026-05-27.
    strikes = [round(2.65 + 0.05 * i, 2) for i in range(14)]
    oi_map = {
        2.65: (1_000, 8_000),
        2.70: (2_000, 15_000),
        2.75: (4_000, 40_000),
        2.80: (6_000, 80_000),
        2.85: (8_000, 35_000),
        2.90: (12_000, 18_000),
        2.95: (20_000, 20_000),
        3.00: (18_000, 10_000),
        3.05: (35_000, 6_000),
        3.10: (80_000, 4_000),
        3.15: (40_000, 2_000),
        3.20: (12_000, 1_000),
        3.25: (5_000, 600),
        3.30: (2_000, 300),
    }

    def _delta(strike: float, cp: str) -> float:
        dist = abs(strike - 2.95)
        mag = max(0.04, 0.50 - dist * 2.2)
        return mag if cp == "C" else -mag

    chain_rows = []
    oi_rows = []
    for dt in dates:
        for strike in strikes:
            call_oi, put_oi = oi_map[strike]
            for cp, oi in (("C", call_oi), ("P", put_oi)):
                code = f"50ETF{'购' if cp == 'C' else '沽'}5月{int(round(strike * 1000))}"
                dist = abs(strike - 2.95)
                px = max(0.008, 0.10 - dist * 0.35)
                chain_rows.append(
                    {
                        "trade_date": dt,
                        "underlying_code": "510050",
                        "contract_code": code,
                        "strike": strike,
                        "cp": cp,
                        "expire_date": "2026-05-27",
                        "option_close": px,
                        "underlying_close": 2.95,
                        "delta": _delta(strike, cp),
                        "gamma": 1.2,
                        "vega": 0.01,
                        "theta": -0.002 * max(0.2, 1.0 - dist),
                        "iv": 0.22,
                    }
                )
                oi_rows.append(
                    {
                        "trade_date": dt,
                        "underlying_code": "510050",
                        "contract_code": code,
                        "open_interest": oi,
                    }
                )
    return und, pd.DataFrame(chain_rows), pd.DataFrame(oi_rows)


def test_parse_etf_option_display_name_and_fourth_wednesday():
    parsed = parse_etf_option_display_name("50ETF沽4月2650", asof="2026-03-27")
    assert parsed is not None
    assert parsed["cp"] == "P"
    assert parsed["strike"] == 2.65
    assert fourth_wednesday(2026, 4).isoformat() == "2026-04-22"
    assert pd.Timestamp(parsed["expire_date"]).date().isoformat() == "2026-04-22"
    call = parse_etf_option_display_name("50ETF购9月3100", asof="2026-08-03")
    assert call["cp"] == "C"
    assert call["strike"] == 3.10


def test_complete_chain_metadata_fills_missing_strike_cp_expire():
    raw = pd.DataFrame(
        [
            {
                "trade_date": "2026-03-27",
                "underlying_code": "510050",
                "contract_code": "50ETF沽4月2650",
                "strike": None,
                "cp": "",
                "expire_date": None,
                "option_close": 0.012,
            },
            {
                "trade_date": "2026-03-28",
                "underlying_code": "510050",
                "contract_code": "50ETF沽4月2650",
                "strike": 2.65,
                "cp": "P",
                "expire_date": "2026-04-22",
                "option_close": 0.011,
            },
        ]
    )
    out = complete_chain_metadata(raw)
    first = out.loc[out["trade_date"] == pd.Timestamp("2026-03-27")].iloc[0]
    assert first["cp"] == "P"
    assert float(first["strike"]) == 2.65
    assert pd.Timestamp(first["expire_date"]).date().isoformat() == "2026-04-22"


def test_research_to_v2_result_scales_returns_to_percent():
    payload = {
        "summary": {
            "initialCapital": 1_000_000,
            "finalEquity": 1_142_390,
            "totalReturn": 0.14239,
            "annualizedReturn": 0.4517,
            "annualizedVol": 0.12,
            "sharpe": 1.68,
            "maxDrawdown": -0.0294,
            "winRate": 0.71,
            "trades": 1,
            "avgTradePnl": 100.0,
            "underlying": "510050",
            "tradingDays": 100,
            "config": {"lots": 120},
        },
        "trades": [
            {
                "entryDate": "2026-04-01",
                "exitDate": "2026-04-20",
                "pnl": 100.0,
                "shortCallCode": "50ETF购5月3100",
                "shortPutCode": "50ETF沽5月2900",
                "longCallCode": "50ETF购5月3200",
                "longPutCode": "50ETF沽5月2800",
                "shortCallStrike": 3.1,
                "shortPutStrike": 2.9,
                "callLots": 120,
                "putLots": 120,
                "entryCredit": 0.04,
                "exitDebit": 0.01,
                "fees": 10,
                "reason": "take_profit",
            }
        ],
        "equityCurve": [{"date": "2026-04-01", "equity": 1_000_000}, {"date": "2026-04-20", "equity": 1_142_390}],
    }
    out = research_to_v2_result(payload, code="stub")
    assert abs(out["totalReturn"] - 14.239) < 1e-6
    assert abs(out["annualizedReturn"] - 45.17) < 1e-6
    assert out["closedTrades"][0]["shortCallCode"] == "50ETF购5月3100"


def test_v2_service_routes_iron_condor_to_listed_chain(tmp_path, monkeypatch):
    und, chain, oi = _synthetic_panel()

    def _loader(underlying, start=None, end=None, data_dir=None):
        del underlying, start, end, data_dir
        return und, chain, oi

    monkeypatch.setattr(
        "app.services.gex_lsp_strangle.v2_adapter.load_listed_option_panel",
        _loader,
    )
    called = {"frames": 0}

    def _frame(*_args, **_kwargs):
        called["frames"] += 1
        raise AssertionError("listed-chain iron condor must not fetch V2 klines")

    code = (REPO_ROOT / "docs/examples/strategy_v2_gex_lsp_iron_condor.py").read_text(encoding="utf-8")
    repository = _Repository()
    service = StrategyV2BacktestService(
        repository=repository,
        frame_fetcher=_frame,
        snapshot_store=MarketDataSnapshotStore(tmp_path),
    )
    run_id, result = service.run(
        user_id=1,
        code=code,
        start_date=datetime(2026, 4, 1),
        end_date=datetime(2026, 5, 15),
        initial_capital=1_000_000,
        persist=True,
        params={"lots": 1, "kelly": False},
        source_id=40,
    )
    assert run_id == 991
    assert called["frames"] == 0
    assert result["engine"]["kind"] == "gex_lsp_iron_condor_research"
    assert result["executionAssumptions"]["contractSelection"] == "listed_chain_gex_walls"
    assert repository.persisted["market"] == "CNIndexOptions"
    trades = result.get("closedTrades") or []
    assert trades
    codes = {item.get("shortCallCode") for item in trades}
    assert all(str(code).startswith("50ETF") for code in codes if code)
    assert "10010975" not in str(result)


def test_run_listed_chain_uses_injected_loader():
    und, chain, oi = _synthetic_panel()
    result = run_listed_chain_iron_condor(
        code="stub",
        underlying="510050",
        start_date=datetime(2026, 4, 1),
        end_date=datetime(2026, 5, 15),
        initial_capital=1_000_000,
        params={"lots": 1},
        loader=lambda *_a, **_k: (und, chain, oi),
    )
    assert result["totalTrades"] >= 1
    assert config_from_params({}, underlying="510050", initial_capital=1_000_000).lots == 80
    assert config_from_params({}, underlying="510050", initial_capital=1_000_000).wing_steps == 3


def test_csv_listed_chain_selects_changing_contracts():
    if not (CSV_DIR / "chain_510050.csv").exists():
        return
    import os

    os.environ["ETF_OPTIONS_CH_ENABLED"] = "0"
    os.environ["GEX_LSP_DATA_DIR"] = str(CSV_DIR)
    from app.services.gex_lsp_strangle.chain_store import load_listed_option_panel

    und, chain, oi = load_listed_option_panel("510050", start="2026-03-27", end="2026-08-31", data_dir=CSV_DIR)
    assert chain["trade_date"].nunique() >= 90
    result = run_iron_condor_backtest(
        und,
        chain,
        oi,
        config=IronCondorBacktestConfig(
            underlying_code="510050",
            lots=80,
            use_kelly_sizing=False,
            require_high_iv=False,
            require_inside_walls=False,
        ),
    )
    assert result.trades
    short_calls = {trade.get("shortCallCode") for trade in result.trades}
    short_puts = {trade.get("shortPutCode") for trade in result.trades}
    assert short_calls
    assert short_puts
    assert not any(str(code).isdigit() and len(str(code)) == 8 for code in short_calls)
    assert all("ETF" in str(code) for code in short_calls)

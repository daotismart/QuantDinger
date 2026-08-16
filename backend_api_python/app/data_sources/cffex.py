"""Compliance-oriented CFFEX market data source.

This source serves ``CNIndexFutures`` / ``CNIndexOptions`` only. It never falls
back to Binance/CCXT or CME Twelve Data paths.

Providers (selected via ``CFFEX_MARKET_DATA_PROVIDER``):
  - ``compliance`` (default): built-in deterministic quotes for paper / runtime
    sizing when a licensed vendor feed is not configured.
  - ``akshare``: optional mainland China public feed when the package is
    installed and the operator opts in. Failures raise — no silent crypto route.
"""

from __future__ import annotations

import hashlib
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.data_sources.base import BaseDataSource, TIMEFRAME_SECONDS
from app.markets.cn_index_derivatives import (
    CFFEX_MARKET_FUTURES,
    CFFEX_MARKET_OPTIONS,
    get_future_spec,
    get_option_spec,
    is_cffex_index_derivative,
    is_cffex_index_future,
    is_cffex_index_option,
    normalize_derivative_symbol,
    parse_future_symbol,
    parse_option_symbol,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Approximate front-month index levels used only by the compliance simulator.
_ROOT_BASE_PRICE = {
    "IF": 3800.0,
    "IH": 2600.0,
    "IC": 5600.0,
    "IM": 5800.0,
    "IO": 3800.0,
    "HO": 2600.0,
    "MO": 5800.0,
}


def _provider_name() -> str:
    return (os.getenv("CFFEX_MARKET_DATA_PROVIDER") or "compliance").strip().lower()


def _session_open_utc() -> bool:
    """Rough CFFEX day session check in China Standard Time (UTC+8)."""
    now = datetime.now(timezone(timedelta(hours=8)))
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    # 09:30-11:30, 13:00-15:00
    return (9 * 60 + 30 <= minutes <= 11 * 60 + 30) or (13 * 60 <= minutes <= 15 * 60)


class CffexDataSource(BaseDataSource):
    """Dedicated CFFEX equity-index futures / options market data."""

    name = "CFFEX"

    def get_kline(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        before_time: Optional[int] = None,
        after_time: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        self._assert_symbol(symbol)
        provider = _provider_name()
        if provider == "akshare":
            rows = self._get_kline_akshare(symbol, timeframe, limit, before_time)
            if rows:
                return self._filter_after(rows, after_time)
            raise ValueError(
                "CFFEX akshare provider returned no bars for "
                f"{normalize_derivative_symbol(symbol)!r}. "
                "Configure a licensed feed or set CFFEX_MARKET_DATA_PROVIDER=compliance."
            )
        rows = self._get_kline_compliance(symbol, timeframe, limit, before_time)
        return self._filter_after(rows, after_time)

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        self._assert_symbol(symbol)
        provider = _provider_name()
        if provider == "akshare":
            ticker = self._get_ticker_akshare(symbol)
            if ticker and float(ticker.get("last") or 0) > 0:
                return ticker
            raise ValueError(
                "CFFEX akshare provider returned an empty ticker for "
                f"{normalize_derivative_symbol(symbol)!r}."
            )
        return self._get_ticker_compliance(symbol)

    def list_contracts(self) -> List[Dict[str, Any]]:
        """Return static root contracts for catalog / symbol master seeding."""
        from app.markets.cn_index_derivatives import CFFEX_FUTURE_SPECS, CFFEX_OPTION_SPECS

        rows: List[Dict[str, Any]] = []
        for spec in CFFEX_FUTURE_SPECS.values():
            rows.append(spec.to_dict())
        for spec in CFFEX_OPTION_SPECS.values():
            rows.append(spec.to_dict())
        return rows

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _assert_symbol(self, symbol: str) -> None:
        if not is_cffex_index_derivative(symbol):
            raise ValueError(
                f"CffexDataSource only accepts CFFEX index futures/options, got {symbol!r}."
            )

    def _root_for(self, symbol: str) -> str:
        if is_cffex_index_future(symbol):
            return parse_future_symbol(symbol)["root"]  # type: ignore[index]
        return parse_option_symbol(symbol)["root"]  # type: ignore[index]

    def _base_price(self, symbol: str) -> float:
        root = self._root_for(symbol)
        base = float(_ROOT_BASE_PRICE.get(root, 3000.0))
        # Mild deterministic drift per instrument id so IF != IF2509.
        digest = hashlib.sha1(normalize_derivative_symbol(symbol).encode("utf-8")).hexdigest()
        bump = (int(digest[:6], 16) % 200) / 10.0  # 0..19.9
        return round(base + bump, 2)

    def _get_ticker_compliance(self, symbol: str) -> Dict[str, Any]:
        last = self._base_price(symbol)
        root = self._root_for(symbol)
        market = CFFEX_MARKET_FUTURES if is_cffex_index_future(symbol) else CFFEX_MARKET_OPTIONS
        tick = (
            get_future_spec(symbol).tick_size
            if is_cffex_index_future(symbol)
            else get_option_spec(symbol).tick_size
        )
        return {
            "symbol": normalize_derivative_symbol(symbol),
            "root": root,
            "market": market,
            "exchange": "CFFEX",
            "last": last,
            "bid": round(last - tick, 2),
            "ask": round(last + tick, 2),
            "provider": "compliance",
            "session_open": _session_open_utc(),
            "timestamp": int(time.time()),
        }

    def _get_kline_compliance(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        before_time: Optional[int],
    ) -> List[Dict[str, Any]]:
        tf = str(timeframe or "1D").strip()
        seconds = int(TIMEFRAME_SECONDS.get(tf, TIMEFRAME_SECONDS.get(tf.upper(), 86400)))
        count = max(1, min(int(limit or 100), 1500))
        end_ts = int(before_time or time.time())
        # Align to candle boundary.
        end_ts = end_ts - (end_ts % seconds)
        base = self._base_price(symbol)
        rows: List[Dict[str, Any]] = []
        for idx in range(count, 0, -1):
            ts = end_ts - idx * seconds
            # Small synthetic oscillation for backtest/paper smoke tests.
            wave = ((idx % 17) - 8) * 0.5
            close = round(base + wave, 2)
            open_px = round(close - 0.4, 2)
            high = round(max(open_px, close) + 0.6, 2)
            low = round(min(open_px, close) - 0.6, 2)
            rows.append(
                self.format_kline(ts, open_px, high, low, close, volume=float(1000 + idx))
            )
        return rows

    def _filter_after(
        self, rows: List[Dict[str, Any]], after_time: Optional[int]
    ) -> List[Dict[str, Any]]:
        if after_time is None:
            return rows
        bound = int(after_time)
        return [row for row in rows if int(row.get("time") or 0) >= bound]

    def _get_ticker_akshare(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            import akshare as ak  # type: ignore
        except Exception as exc:
            raise ValueError(
                "CFFEX_MARKET_DATA_PROVIDER=akshare requires the akshare package."
            ) from exc

        code = normalize_derivative_symbol(symbol)
        try:
            # futures_zh_spot covers mainland commodity/index futures quotes.
            frame = ak.futures_zh_spot(symbol=code, market="CF", adjust="0")
            if frame is None or getattr(frame, "empty", True):
                return None
            row = frame.iloc[-1]
            last = float(row.get("current_price") or row.get("close") or row.get("最新价") or 0)
            if last <= 0:
                return None
            return {
                "symbol": code,
                "last": last,
                "provider": "akshare",
                "exchange": "CFFEX",
                "raw": row.to_dict() if hasattr(row, "to_dict") else {},
            }
        except Exception as exc:
            logger.warning("CFFEX akshare ticker failed for %s: %s", code, exc)
            raise ValueError(f"CFFEX akshare ticker failed for {code}: {exc}") from exc

    def _get_kline_akshare(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        before_time: Optional[int],
    ) -> List[Dict[str, Any]]:
        try:
            import akshare as ak  # type: ignore
        except Exception as exc:
            raise ValueError(
                "CFFEX_MARKET_DATA_PROVIDER=akshare requires the akshare package."
            ) from exc

        code = normalize_derivative_symbol(symbol)
        if is_cffex_index_option(code):
            raise ValueError(
                "CFFEX akshare K-line path currently supports index futures only; "
                "use CFFEX_MARKET_DATA_PROVIDER=compliance for options paper data."
            )
        try:
            frame = ak.futures_zh_daily_sina(symbol=code)
        except Exception as exc:
            raise ValueError(f"CFFEX akshare daily bars failed for {code}: {exc}") from exc
        if frame is None or getattr(frame, "empty", True):
            return []
        rows: List[Dict[str, Any]] = []
        for _, item in frame.tail(max(1, int(limit or 100))).iterrows():
            try:
                day = str(item.get("date") or item.get("日期") or "")
                ts = int(datetime.strptime(day[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
                if before_time is not None and ts >= int(before_time):
                    continue
                rows.append(
                    self.format_kline(
                        ts,
                        float(item.get("open") or item.get("开盘价") or 0),
                        float(item.get("high") or item.get("最高价") or 0),
                        float(item.get("low") or item.get("最低价") or 0),
                        float(item.get("close") or item.get("收盘价") or 0),
                        float(item.get("volume") or item.get("成交量") or 0),
                    )
                )
            except Exception:
                continue
        return rows

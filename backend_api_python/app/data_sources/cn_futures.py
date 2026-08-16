"""Compliance-oriented mainland China futures & futures-options market data.

Serves ``CNFutures`` / ``CNFuturesOptions`` / ``CNIndexFutures`` /
``CNIndexOptions``. Never falls back to Binance/CCXT or CME Twelve Data.

Providers (``CN_FUTURES_MARKET_DATA_PROVIDER`` or legacy
``CFFEX_MARKET_DATA_PROVIDER``):
  - ``compliance`` (default): deterministic paper quotes
  - ``akshare``: optional public feed when installed
"""

from __future__ import annotations

import hashlib
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.data_sources.base import BaseDataSource, TIMEFRAME_SECONDS
from app.markets.cn_futures import (
    CN_FUTURES_MARKET,
    CN_FUTURES_OPTIONS_MARKET,
    get_future_product,
    is_cn_derivative,
    is_cn_future,
    is_cn_futures_option,
    normalize_cn_symbol,
    parse_cn_future_symbol,
    parse_cn_option_symbol,
    resolve_market_category,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _provider_name() -> str:
    return (
        os.getenv("CN_FUTURES_MARKET_DATA_PROVIDER")
        or os.getenv("CFFEX_MARKET_DATA_PROVIDER")
        or "compliance"
    ).strip().lower()


def _session_open_cst() -> bool:
    now = datetime.now(timezone(timedelta(hours=8)))
    if now.weekday() >= 5:
        return False
    minutes = now.hour * 60 + now.minute
    # Day session approx 09:00-15:00; night session products open ~21:00.
    day = 9 * 60 <= minutes <= 15 * 60
    night = minutes >= 21 * 60 or minutes <= 2 * 60 + 30
    return day or night


class CnFuturesDataSource(BaseDataSource):
    """Dedicated mainland China futures / futures-options market data."""

    name = "CNFutures"

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
                "CN futures akshare provider returned no bars for "
                f"{normalize_cn_symbol(symbol)!r}. "
                "Set CN_FUTURES_MARKET_DATA_PROVIDER=compliance for paper data."
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
                "CN futures akshare provider returned an empty ticker for "
                f"{normalize_cn_symbol(symbol)!r}."
            )
        return self._get_ticker_compliance(symbol)

    def list_contracts(self) -> List[Dict[str, Any]]:
        from app.markets.cn_futures import list_products

        return [p.to_dict() for p in list_products()]

    def _assert_symbol(self, symbol: str) -> None:
        if not is_cn_derivative(symbol):
            raise ValueError(
                f"CnFuturesDataSource only accepts mainland China futures/options, got {symbol!r}."
            )

    def _root_for(self, symbol: str) -> str:
        if is_cn_future(symbol):
            return parse_cn_future_symbol(symbol)["root"]  # type: ignore[index]
        return parse_cn_option_symbol(symbol)["root"]  # type: ignore[index]

    def _base_price(self, symbol: str) -> float:
        product = get_future_product(symbol)
        base = float(product.base_price or 3000.0)
        digest = hashlib.sha1(normalize_cn_symbol(symbol).encode("utf-8")).hexdigest()
        bump = (int(digest[:6], 16) % 200) / 10.0
        return round(base + bump, 2)

    def _get_ticker_compliance(self, symbol: str) -> Dict[str, Any]:
        last = self._base_price(symbol)
        product = get_future_product(symbol)
        tick = float(
            product.option_tick_size
            if is_cn_futures_option(symbol) and product.option_tick_size
            else product.tick_size
        )
        return {
            "symbol": normalize_cn_symbol(symbol),
            "root": product.root,
            "market": resolve_market_category(symbol) or CN_FUTURES_MARKET,
            "exchange": product.exchange,
            "last": last,
            "bid": round(last - tick, 4),
            "ask": round(last + tick, 4),
            "provider": "compliance",
            "session_open": _session_open_cst(),
            "night_session": product.night_session,
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
        end_ts = end_ts - (end_ts % seconds)
        base = self._base_price(symbol)
        product = get_future_product(symbol)
        step = max(float(product.tick_size), 0.01)
        rows: List[Dict[str, Any]] = []
        for idx in range(count, 0, -1):
            ts = end_ts - idx * seconds
            wave = ((idx % 17) - 8) * step
            close = round(base + wave, 4)
            open_px = round(close - step, 4)
            high = round(max(open_px, close) + step, 4)
            low = round(min(open_px, close) - step, 4)
            rows.append(self.format_kline(ts, open_px, high, low, close, volume=float(1000 + idx)))
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
                "CN_FUTURES_MARKET_DATA_PROVIDER=akshare requires the akshare package."
            ) from exc
        code = normalize_cn_symbol(symbol)
        try:
            frame = ak.futures_zh_spot(symbol=code, market="CF", adjust="0")
            if frame is None or getattr(frame, "empty", True):
                return None
            row = frame.iloc[-1]
            last = float(row.get("current_price") or row.get("close") or row.get("最新价") or 0)
            if last <= 0:
                return None
            product = get_future_product(symbol)
            return {
                "symbol": code,
                "last": last,
                "provider": "akshare",
                "exchange": product.exchange,
                "raw": row.to_dict() if hasattr(row, "to_dict") else {},
            }
        except Exception as exc:
            logger.warning("CN futures akshare ticker failed for %s: %s", code, exc)
            raise ValueError(f"CN futures akshare ticker failed for {code}: {exc}") from exc

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
                "CN_FUTURES_MARKET_DATA_PROVIDER=akshare requires the akshare package."
            ) from exc
        code = normalize_cn_symbol(symbol)
        if is_cn_futures_option(code) and not is_cn_future(code):
            raise ValueError(
                "CN futures akshare K-line currently supports futures underlyings; "
                "use CN_FUTURES_MARKET_DATA_PROVIDER=compliance for options paper data."
            )
        try:
            frame = ak.futures_zh_daily_sina(symbol=code)
        except Exception as exc:
            raise ValueError(f"CN futures akshare daily bars failed for {code}: {exc}") from exc
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


# Back-compat alias for previous CFFEX-only import path.
class CffexDataSource(CnFuturesDataSource):
    name = "CFFEX"

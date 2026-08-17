"""Compliance-oriented mainland China futures & futures-options market data.

Serves ``CNFutures`` / ``CNFuturesOptions`` / ``CNIndexFutures`` /
``CNIndexOptions``. Never falls back to Binance/CCXT or CME Twelve Data.

Providers (``CN_FUTURES_MARKET_DATA_PROVIDER`` or legacy
``CFFEX_MARKET_DATA_PROVIDER``):
  - ``auto`` (default): prefer akshare full history, fall back to compliance
  - ``akshare``: public mainland feeds (Sina daily/minute, main continuous)
  - ``compliance``: deterministic paper quotes for offline/CI
"""

from __future__ import annotations

import hashlib
import os
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.data_sources.base import BaseDataSource, TIMEFRAME_SECONDS
from app.markets.cn_futures import (
    CN_FUTURES_MARKET,
    get_future_product,
    is_cn_derivative,
    is_cn_future,
    is_cn_futures_option,
    normalize_cn_symbol,
    parse_cn_future_symbol,
    parse_cn_option_symbol,
    resolve_market_category,
)
from app.markets.cn_futures_sessions import md_connection_open
from app.utils.logger import get_logger

logger = get_logger(__name__)

_CST = timezone(timedelta(hours=8))

_MINUTE_PERIOD_MAP = {
    "1m": "1",
    "3m": "1",  # resampled from 1m
    "5m": "5",
    "15m": "15",
    "30m": "30",
    "1H": "60",
    "1h": "60",
}

# How many nearby delivery months to stitch when building deeper minute history.
_MINUTE_STITCH_MONTHS = max(1, int(os.getenv("CN_FUTURES_MINUTE_STITCH_MONTHS", "12") or 12))


def _provider_name() -> str:
    return (
        os.getenv("CN_FUTURES_MARKET_DATA_PROVIDER")
        or os.getenv("CFFEX_MARKET_DATA_PROVIDER")
        or "auto"
    ).strip().lower()


def _session_open_cst() -> bool:
    return md_connection_open([])


def _to_cst_ts(day_value: Any) -> Optional[int]:
    """Convert China-session date/datetime values to Unix seconds (CST)."""
    try:
        if isinstance(day_value, datetime):
            dt = day_value
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=_CST)
            return int(dt.timestamp())
        if isinstance(day_value, date) and not isinstance(day_value, datetime):
            dt = datetime(day_value.year, day_value.month, day_value.day, tzinfo=_CST)
            return int(dt.timestamp())
        text = str(day_value or "").strip()
        if not text:
            return None
        if " " in text or "T" in text:
            normalized = text.replace("T", " ")[:19]
            dt = datetime.strptime(normalized, "%Y-%m-%d %H:%M:%S").replace(tzinfo=_CST)
            return int(dt.timestamp())
        dt = datetime.strptime(text[:10], "%Y-%m-%d").replace(tzinfo=_CST)
        return int(dt.timestamp())
    except Exception:
        return None


# Back-compat alias used by older call sites / tests.
_to_cst_midnight_ts = _to_cst_ts


def resolve_history_symbol(symbol: str) -> Tuple[str, str]:
    """Return ``(fetch_symbol, mode)`` for Sina/akshare.

    mode:
      - ``continuous``: main-continuous root code like ``RB0`` / ``IF0``
      - ``contract``: specific delivery month like ``RB2509``
    """
    code = normalize_cn_symbol(symbol)
    parsed = parse_cn_future_symbol(code)
    if parsed:
        root = parsed["root"]
        month = parsed.get("month") or ""
        if not month or month in ("0", "888", "999"):
            return f"{root}0", "continuous"
        return f"{root}{month}", "contract"
    # Options: fall back to underlying continuous for reference history.
    opt = parse_cn_option_symbol(code)
    if opt:
        return f"{opt['root']}0", "continuous"
    # Bare continuous forms that slip past the futures parser.
    if code.endswith("0") and len(code) >= 2:
        maybe_root = code[:-1]
        from app.markets.cn_futures import CN_FUTURE_PRODUCTS

        if maybe_root in CN_FUTURE_PRODUCTS:
            return f"{maybe_root}0", "continuous"
    return code, "contract"


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
        lim = max(1, int(limit or 300))
        # Large limits / after_time windows request the full available history.
        want_full = lim >= 5000 or after_time is not None
        rows = self._fetch_history_rows(
            symbol,
            timeframe,
            before_time=before_time,
            after_time=after_time,
            prefer_full=want_full,
        )
        return self.filter_and_limit(
            rows,
            limit=lim,
            before_time=before_time,
            after_time=after_time,
            truncate=(after_time is None),
        )

    def get_history(
        self,
        symbol: str,
        timeframe: str = "1D",
        *,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return the complete available history in ``[start, end)``.

        Dates are interpreted as China calendar days (CST). When both bounds
        are omitted, returns the full series from the upstream feed.
        """
        self._assert_symbol(symbol)
        after_time = start_time
        before_time = end_time
        if start_date and after_time is None:
            after_time = _to_cst_midnight_ts(start_date)
        if end_date and before_time is None:
            # exclusive end: next CST midnight
            ts = _to_cst_midnight_ts(end_date)
            if ts is not None:
                before_time = ts + 86400
        rows = self._fetch_history_rows(
            symbol,
            timeframe,
            before_time=before_time,
            after_time=after_time,
            prefer_full=True,
        )
        return self.filter_and_limit(
            rows,
            limit=10_000_000,
            before_time=before_time,
            after_time=after_time,
            truncate=False,
        )

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        self._assert_symbol(symbol)
        provider = _provider_name()
        if provider in ("akshare", "auto"):
            try:
                ticker = self._get_ticker_akshare(symbol)
                if ticker and float(ticker.get("last") or 0) > 0:
                    return ticker
                if provider == "akshare":
                    raise ValueError(
                        "CN futures akshare provider returned an empty ticker for "
                        f"{normalize_cn_symbol(symbol)!r}."
                    )
            except Exception as exc:
                if provider == "akshare":
                    raise
                logger.info("CN futures ticker falling back to compliance: %s", exc)
        return self._get_ticker_compliance(symbol)

    def list_contracts(self) -> List[Dict[str, Any]]:
        from app.markets.cn_futures import list_products

        return [p.to_dict() for p in list_products()]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _assert_symbol(self, symbol: str) -> None:
        if not is_cn_derivative(symbol):
            raise ValueError(
                f"CnFuturesDataSource only accepts mainland China futures/options, got {symbol!r}."
            )

    def _fetch_history_rows(
        self,
        symbol: str,
        timeframe: str,
        *,
        before_time: Optional[int],
        after_time: Optional[int],
        prefer_full: bool,
    ) -> List[Dict[str, Any]]:
        provider = _provider_name()
        if provider in ("akshare", "auto"):
            try:
                rows = self._get_history_akshare(
                    symbol,
                    timeframe,
                    before_time=before_time,
                    after_time=after_time,
                    prefer_full=prefer_full,
                )
                if rows:
                    return rows
                if provider == "akshare":
                    raise ValueError(
                        "CN futures akshare provider returned no bars for "
                        f"{normalize_cn_symbol(symbol)!r}."
                    )
            except Exception as exc:
                if provider == "akshare":
                    raise
                logger.info("CN futures history falling back to compliance: %s", exc)
        return self._get_kline_compliance(
            symbol,
            timeframe,
            limit=1500 if not prefer_full else 5000,
            before_time=before_time,
        )

    def _normalize_tf(self, timeframe: str) -> str:
        raw = str(timeframe or "1D").strip()
        aliases = {
            "d": "1D",
            "day": "1D",
            "daily": "1D",
            "w": "1W",
            "week": "1W",
            "weekly": "1W",
            "3min": "3m",
            "5min": "5m",
            "15min": "15m",
            "30min": "30m",
            "60m": "1H",
            "60min": "1H",
            "h1": "1H",
            "4h": "4H",
        }
        key = raw.lower()
        if key in aliases:
            return aliases[key]
        if raw in TIMEFRAME_SECONDS or raw in _MINUTE_PERIOD_MAP:
            return raw
        upper = raw.upper()
        if upper in TIMEFRAME_SECONDS:
            return upper
        return "1D"

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
        tf = self._normalize_tf(timeframe)
        seconds = int(TIMEFRAME_SECONDS.get(tf, 86400))
        count = max(1, min(int(limit or 100), 5000))
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

    def _import_akshare(self):
        try:
            import akshare as ak  # type: ignore
            return ak
        except Exception as exc:
            raise ValueError(
                "CN futures history requires the akshare package "
                "(pip install akshare) or set CN_FUTURES_MARKET_DATA_PROVIDER=compliance."
            ) from exc

    def _get_ticker_akshare(self, symbol: str) -> Optional[Dict[str, Any]]:
        ak = self._import_akshare()
        fetch_symbol, _mode = resolve_history_symbol(symbol)
        # Spot endpoint prefers contract codes; continuous roots often work as ROOT0.
        code = normalize_cn_symbol(symbol)
        query = code if parse_cn_future_symbol(code) and parse_cn_future_symbol(code).get("month") else fetch_symbol
        try:
            frame = ak.futures_zh_spot(symbol=query, market="CF", adjust="0")
            if frame is None or getattr(frame, "empty", True):
                # Fall back to last daily close.
                daily = self._load_daily_frame(ak, fetch_symbol)
                if daily is None or daily.empty:
                    return None
                last_row = daily.iloc[-1]
                last = float(last_row.get("close") or last_row.get("收盘价") or 0)
                if last <= 0:
                    return None
                product = get_future_product(symbol)
                return {
                    "symbol": code,
                    "last": last,
                    "provider": "akshare",
                    "exchange": product.exchange,
                    "history_symbol": fetch_symbol,
                }
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
                "history_symbol": fetch_symbol,
                "raw": row.to_dict() if hasattr(row, "to_dict") else {},
            }
        except Exception as exc:
            logger.warning("CN futures akshare ticker failed for %s: %s", code, exc)
            raise ValueError(f"CN futures akshare ticker failed for {code}: {exc}") from exc

    def _load_daily_frame(self, ak: Any, fetch_symbol: str):
        """Load the longest available daily series for a Sina symbol."""
        try:
            frame = ak.futures_zh_daily_sina(symbol=fetch_symbol)
            if frame is not None and not getattr(frame, "empty", True):
                return frame
        except Exception as exc:
            logger.debug("futures_zh_daily_sina failed for %s: %s", fetch_symbol, exc)
        # Main-continuous helper accepts start/end and Chinese column names.
        try:
            frame = ak.futures_main_sina(
                symbol=fetch_symbol,
                start_date="19900101",
                end_date="20500101",
            )
            if frame is not None and not getattr(frame, "empty", True):
                return frame
        except Exception as exc:
            logger.debug("futures_main_sina failed for %s: %s", fetch_symbol, exc)
        return None

    def _frame_to_daily_rows(self, frame: Any) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for _, item in frame.iterrows():
            day = item.get("date") or item.get("日期") or item.get("datetime")
            ts = _to_cst_midnight_ts(day)
            if ts is None:
                continue
            try:
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
        rows.sort(key=lambda r: r["time"])
        return rows

    def _load_minute_rows(self, ak: Any, fetch_symbol: str, period: str) -> List[Dict[str, Any]]:
        try:
            frame = ak.futures_zh_minute_sina(symbol=fetch_symbol, period=period)
        except Exception as exc:
            logger.debug("minute fetch failed for %s period=%s: %s", fetch_symbol, period, exc)
            return []
        if frame is None or getattr(frame, "empty", True):
            return []
        rows: List[Dict[str, Any]] = []
        for _, item in frame.iterrows():
            raw_dt = item.get("datetime") or item.get("date") or item.get("时间")
            ts = _to_cst_ts(raw_dt)
            if ts is None:
                continue
            try:
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
        rows.sort(key=lambda r: r["time"])
        return rows

    def _candidate_minute_symbols(self, symbol: str, *, months: int) -> List[str]:
        """Build continuous + nearby dated contract codes for minute stitching."""
        code = normalize_cn_symbol(symbol)
        fetch_symbol, mode = resolve_history_symbol(code)
        parsed = parse_cn_future_symbol(code) or parse_cn_option_symbol(code)
        if not parsed:
            return [fetch_symbol]
        root = parsed["root"]
        product = get_future_product(root)
        out: List[str] = []
        seen = set()

        def _add(sym: str) -> None:
            key = sym.upper()
            if key not in seen:
                seen.add(key)
                out.append(key)

        # Prefer continuous feed when available (recent window).
        _add(f"{root}0")
        if mode == "contract" and parsed.get("month") and parsed["month"] not in ("0", "888", "999"):
            _add(f"{root}{parsed['month']}")

        now = datetime.now(_CST)
        year, month = now.year, now.month
        index_like = product.exchange == "CFFEX" and product.product_class in ("index", "financial")
        for _ in range(max(1, int(months)) * (4 if index_like else 1) + 2):
            if index_like:
                # Equity-index / treasury: mainly Mar/Jun/Sep/Dec cycle.
                if month in (3, 6, 9, 12):
                    _add(f"{root}{year % 100:02d}{month:02d}")
            else:
                _add(f"{root}{year % 100:02d}{month:02d}")
            month -= 1
            if month <= 0:
                month = 12
                year -= 1
            if len(out) >= months + 3:
                break
        return out

    def _merge_minute_rows(self, chunks: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        merged: Dict[int, Dict[str, Any]] = {}
        for rows in chunks:
            for row in rows:
                ts = int(row["time"])
                prev = merged.get(ts)
                if prev is None or float(row.get("volume") or 0) >= float(prev.get("volume") or 0):
                    merged[ts] = row
        return [merged[k] for k in sorted(merged)]

    def _load_minute_history(
        self,
        ak: Any,
        symbol: str,
        period: str,
        *,
        prefer_full: bool,
    ) -> List[Dict[str, Any]]:
        """Load minute bars, optionally stitching nearby contracts for depth.

        Sina ``getFewMinLine`` returns ~1023 bars per symbol/period. Stitching
        successive delivery months yields multi-month intraday history.
        """
        fetch_symbol, mode = resolve_history_symbol(symbol)
        primary = self._load_minute_rows(ak, fetch_symbol, period)
        if not prefer_full:
            if primary:
                return primary
            # Continuous sometimes needs a dated fallback even for short windows.
            for cand in self._candidate_minute_symbols(symbol, months=3):
                if cand == fetch_symbol:
                    continue
                rows = self._load_minute_rows(ak, cand, period)
                if rows:
                    return rows
            return []

        months = _MINUTE_STITCH_MONTHS
        candidates = self._candidate_minute_symbols(symbol, months=months)
        chunks: List[List[Dict[str, Any]]] = []
        if primary:
            chunks.append(primary)
        for cand in candidates:
            if cand == fetch_symbol:
                continue
            rows = self._load_minute_rows(ak, cand, period)
            if rows:
                chunks.append(rows)
                logger.debug(
                    "stitched minute chunk %s period=%s bars=%s %s->%s",
                    cand,
                    period,
                    len(rows),
                    rows[0]["time"],
                    rows[-1]["time"],
                )
        if not chunks:
            return []
        merged = self._merge_minute_rows(chunks)
        logger.info(
            "CN futures minute history symbol=%s period=%s chunks=%s bars=%s",
            normalize_cn_symbol(symbol),
            period,
            len(chunks),
            len(merged),
        )
        return merged

    def _resample(self, rows: List[Dict[str, Any]], seconds: int) -> List[Dict[str, Any]]:
        if not rows or seconds <= 0:
            return rows
        buckets: Dict[int, Dict[str, Any]] = {}
        order: List[int] = []
        for row in rows:
            ts = int(row["time"])
            bucket = ts - (ts % seconds)
            if bucket not in buckets:
                buckets[bucket] = {
                    "time": bucket,
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]),
                }
                order.append(bucket)
            else:
                cur = buckets[bucket]
                cur["high"] = max(cur["high"], float(row["high"]))
                cur["low"] = min(cur["low"], float(row["low"]))
                cur["close"] = float(row["close"])
                cur["volume"] = float(cur["volume"]) + float(row["volume"])
        return [self.format_kline(
            buckets[key]["time"],
            buckets[key]["open"],
            buckets[key]["high"],
            buckets[key]["low"],
            buckets[key]["close"],
            buckets[key]["volume"],
        ) for key in order]

    def _get_history_akshare(
        self,
        symbol: str,
        timeframe: str,
        *,
        before_time: Optional[int],
        after_time: Optional[int],
        prefer_full: bool,
    ) -> List[Dict[str, Any]]:
        ak = self._import_akshare()
        tf = self._normalize_tf(timeframe)
        fetch_symbol, mode = resolve_history_symbol(symbol)
        # Specific option contracts have no public long history — use underlying continuous.
        if is_cn_futures_option(symbol) and not is_cn_future(symbol):
            logger.info(
                "CN futures options history uses underlying continuous %s for %s",
                fetch_symbol,
                normalize_cn_symbol(symbol),
            )

        if tf in ("1m", "3m", "5m", "15m", "30m", "1H"):
            period = _MINUTE_PERIOD_MAP[tf]
            rows = self._load_minute_history(
                ak, symbol, period, prefer_full=prefer_full or after_time is not None
            )
            if not rows:
                raise ValueError(
                    f"Minute history unavailable for {normalize_cn_symbol(symbol)!r}. "
                    "Try a dated contract (e.g. RB2509) or continuous root (RB0)."
                )
            if tf == "3m":
                return self._resample(rows, 180)
            return rows

        if tf == "4H":
            minute_rows = self._load_minute_history(
                ak, symbol, "60", prefer_full=prefer_full or after_time is not None
            )
            if not minute_rows:
                raise ValueError(
                    f"4H history unavailable for {normalize_cn_symbol(symbol)!r}; "
                    "pass RB0 / RB2509 style symbols."
                )
            return self._resample(minute_rows, TIMEFRAME_SECONDS["4H"])

        # Daily / weekly — load the complete series then optionally resample.
        frame = self._load_daily_frame(ak, fetch_symbol)
        if frame is None or getattr(frame, "empty", True):
            return []
        rows = self._frame_to_daily_rows(frame)
        if tf in ("1W", "1w"):
            return self._resample(rows, TIMEFRAME_SECONDS["1W"])
        return rows


# Back-compat alias for previous CFFEX-only import path.
class CffexDataSource(CnFuturesDataSource):
    name = "CFFEX"

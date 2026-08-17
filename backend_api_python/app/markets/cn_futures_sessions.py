"""Mainland China futures matching-session calendar (CST).

Used to gate CTP tick collection: connect/subscribe only while a contract's
main session is open (plus a short pre-open buffer), and skip stale-tick
resubscribe while the venue is closed.

Times follow the common SHFE/DCE/CZCE/INE/CFFEX/GFEX published blocks.
Holiday calendars are not applied; weekends and Friday-night / Sunday-night
rules are.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, List, Optional, Sequence, Tuple

from app.markets.cn_futures import get_future_product

_CST = timezone(timedelta(hours=8))

# Inclusive start, exclusive end, minutes from midnight. end < start => wraps.
SessionWindow = Tuple[int, int]

DAY_COMMODITY: Tuple[SessionWindow, ...] = (
    (9 * 60, 10 * 60 + 15),
    (10 * 60 + 30, 11 * 60 + 30),
    (13 * 60 + 30, 15 * 60),
)
DAY_CFFEX_INDEX: Tuple[SessionWindow, ...] = (
    (9 * 60 + 30, 11 * 60 + 30),
    (13 * 60, 15 * 60),
)
DAY_CFFEX_BOND: Tuple[SessionWindow, ...] = (
    (9 * 60 + 30, 11 * 60 + 30),
    (13 * 60, 15 * 60 + 15),
)

NIGHT_2300: SessionWindow = (21 * 60, 23 * 60)
NIGHT_0100: SessionWindow = (21 * 60, 1 * 60)
NIGHT_0230: SessionWindow = (21 * 60, 2 * 60 + 30)

# 21:00-02:30
_NIGHT_0230_ROOTS = frozenset({"AU", "AG", "SC"})
# 21:00-01:00
_NIGHT_0100_ROOTS = frozenset({"CU", "AL", "ZN", "PB", "NI", "SN", "SS", "AO", "BC"})

_CFFEX_INDEX_ROOTS = frozenset({"IF", "IH", "IC", "IM", "IO", "HO", "MO"})
_CFFEX_BOND_ROOTS = frozenset({"T", "TF", "TS", "TL"})


def _truthy(value: Optional[str]) -> bool:
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


def ignore_session_gate() -> bool:
    """Operator override: collect/reconnect regardless of session hours."""
    return _truthy(os.getenv("CTP_MD_IGNORE_SESSION"))


def session_preopen_minutes() -> int:
    return max(0, int(os.getenv("CTP_MD_SESSION_PREOPEN_MINUTES", "10") or 10))


def session_postclose_minutes() -> int:
    return max(0, int(os.getenv("CTP_MD_SESSION_POSTCLOSE_MINUTES", "2") or 2))


def now_cst(now: Optional[datetime] = None) -> datetime:
    if now is None:
        return datetime.now(_CST)
    if now.tzinfo is None:
        return now.replace(tzinfo=_CST)
    return now.astimezone(_CST)


def _minutes_of_day(dt: datetime) -> int:
    return dt.hour * 60 + dt.minute


def _expand_window(window: SessionWindow, *, preopen: int, postclose: int) -> SessionWindow:
    start, end = window
    start = (start - preopen) % (24 * 60)
    end = (end + postclose) % (24 * 60)
    if start == end:
        # Full-day after expansion; treat as always-open wrap.
        return (0, 24 * 60)
    return (start, end)


def _in_window(minutes: int, window: SessionWindow) -> bool:
    start, end = window
    if start == 0 and end == 24 * 60:
        return True
    if start <= end:
        return start <= minutes < end
    return minutes >= start or minutes < end


def _night_window_for_root(root: str) -> Optional[SessionWindow]:
    if root in _NIGHT_0230_ROOTS:
        return NIGHT_0230
    if root in _NIGHT_0100_ROOTS:
        return NIGHT_0100
    try:
        product = get_future_product(root)
    except ValueError:
        return None
    if not product.night_session:
        return None
    return NIGHT_2300


def _day_envelope(root: str) -> SessionWindow:
    """Coarse weekday envelope (stay connected through tea/lunch breaks)."""
    if root in _CFFEX_BOND_ROOTS:
        return (9 * 60 + 20, 15 * 60 + 20)
    if root in _CFFEX_INDEX_ROOTS:
        return (9 * 60 + 20, 15 * 60 + 5)
    try:
        product = get_future_product(root)
        if product.exchange == "CFFEX":
            if product.product_class == "financial":
                return (9 * 60 + 20, 15 * 60 + 20)
            return (9 * 60 + 20, 15 * 60 + 5)
    except ValueError:
        pass
    return (8 * 60 + 50, 15 * 60 + 5)


def _day_windows_for_root(root: str) -> Tuple[SessionWindow, ...]:
    if root in _CFFEX_INDEX_ROOTS:
        return DAY_CFFEX_INDEX
    if root in _CFFEX_BOND_ROOTS:
        return DAY_CFFEX_BOND
    try:
        product = get_future_product(root)
        if product.exchange == "CFFEX":
            if product.product_class == "financial":
                return DAY_CFFEX_BOND
            return DAY_CFFEX_INDEX
    except ValueError:
        pass
    return DAY_COMMODITY


def _root_of(symbol: str) -> str:
    try:
        return str(get_future_product(symbol).root)
    except ValueError:
        text = str(symbol or "").strip()
        if ":" in text:
            text = text.split(":", 1)[-1]
        if "." in text:
            text = text.rsplit(".", 1)[-1]
        letters = "".join(ch for ch in text if ch.isalpha())
        return letters.upper()


def _is_night_session_day(weekday: int, minutes: int, window: SessionWindow) -> bool:
    """Whether this CST instant is on a night-session calendar.

    Night sessions run Sunday 21:00 through Friday night (into Saturday
    morning for wrap-around products). Saturday 21:00 is closed.
    """
    start, end = window
    wraps = start > end
    if wraps:
        if minutes >= start:
            # Evening: Sun-Fri
            return weekday in {0, 1, 2, 3, 4, 6}
        if minutes < end:
            # After midnight: Mon-Sat (following Sun-Fri evenings)
            return weekday in {0, 1, 2, 3, 4, 5}
        return False
    # Same-calendar-day night (21:00-23:00): Sun-Fri only.
    return weekday in {0, 1, 2, 3, 4, 6}


@dataclass(frozen=True)
class SessionStatus:
    symbol: str
    root: str
    in_session: bool
    in_collect_window: bool
    phase: str  # closed | day | night | preopen | postclose


def session_windows(symbol: str) -> Tuple[Tuple[SessionWindow, ...], Optional[SessionWindow]]:
    root = _root_of(symbol)
    return _day_windows_for_root(root), _night_window_for_root(root)


def instrument_session_status(
    symbol: str,
    *,
    now: Optional[datetime] = None,
    preopen_minutes: Optional[int] = None,
    postclose_minutes: Optional[int] = None,
) -> SessionStatus:
    dt = now_cst(now)
    minutes = _minutes_of_day(dt)
    weekday = dt.weekday()
    root = _root_of(symbol)
    day_windows, night_window = session_windows(symbol)
    preopen = session_preopen_minutes() if preopen_minutes is None else max(0, int(preopen_minutes))
    postclose = session_postclose_minutes() if postclose_minutes is None else max(0, int(postclose_minutes))

    in_day = False
    if weekday < 5:
        in_day = any(_in_window(minutes, win) for win in day_windows)
    in_night = False
    if night_window is not None and _is_night_session_day(weekday, minutes, night_window):
        in_night = _in_window(minutes, night_window)

    in_session = bool(in_day or in_night)

    day_env = _expand_window(_day_envelope(root), preopen=preopen, postclose=postclose)
    in_day_env = weekday < 5 and _in_window(minutes, day_env)
    in_night_env = False
    if night_window is not None:
        night_env = _expand_window(night_window, preopen=preopen, postclose=postclose)
        in_night_env = _is_night_session_day(weekday, minutes, night_env) and _in_window(minutes, night_env)

    collect = bool(in_day_env or in_night_env)
    phase = "closed"
    if in_day:
        phase = "day"
    elif in_night:
        phase = "night"
    elif collect:
        phase = "preopen" if minutes >= 18 * 60 or minutes < 8 * 60 else "day"

    if ignore_session_gate():
        return SessionStatus(symbol=symbol, root=root, in_session=True, in_collect_window=True, phase="ignored")
    return SessionStatus(
        symbol=symbol,
        root=root,
        in_session=in_session,
        in_collect_window=collect,
        phase=phase,
    )


def is_instrument_in_session(symbol: str, *, now: Optional[datetime] = None) -> bool:
    return instrument_session_status(symbol, now=now).in_session


def is_instrument_in_collect_window(symbol: str, *, now: Optional[datetime] = None) -> bool:
    return instrument_session_status(symbol, now=now).in_collect_window


def filter_collectible_instruments(
    symbols: Iterable[str],
    *,
    now: Optional[datetime] = None,
) -> List[str]:
    out: List[str] = []
    for symbol in symbols:
        text = str(symbol or "").strip()
        if not text:
            continue
        if is_instrument_in_collect_window(text, now=now):
            out.append(text)
    return out


def any_collectible(symbols: Sequence[str], *, now: Optional[datetime] = None) -> bool:
    items = [str(s).strip() for s in (symbols or []) if str(s).strip()]
    if ignore_session_gate():
        return True
    if not items:
        # No explicit watchlist: use a union of common day+night connection hours.
        dt = now_cst(now)
        minutes = _minutes_of_day(dt)
        weekday = dt.weekday()
        day_open = weekday < 5 and (8 * 60 + 50) <= minutes < (15 * 60 + 20)
        night_open = _is_night_session_day(weekday, minutes, NIGHT_0230) and _in_window(
            minutes, _expand_window(NIGHT_0230, preopen=10, postclose=5)
        )
        return bool(day_open or night_open)
    return any(is_instrument_in_collect_window(item, now=now) for item in items)


def md_connection_open(symbols: Sequence[str], *, now: Optional[datetime] = None) -> bool:
    """Whether the MdApi front should stay connected for this watchlist."""
    return any_collectible(symbols, now=now)

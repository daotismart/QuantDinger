"""Listed-option chain query: filter by underlying, DTE, and delta."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence

from app.markets.cn_options import (
    cn_etf_stock_symbol,
    parse_option_expire_date,
)
from app.services.cn_options_chain import listed_option_catalog
from app.services.options_desk.greeks import align_strike_to_spot, black_scholes_greeks
from app.services.options_desk.iv_rank import realized_vol_from_closes
from app.utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_RATE = 0.02
_DEFAULT_SIGMA = 0.20


def _as_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    iso = parse_option_expire_date(value)
    if not iso:
        return None
    return date.fromisoformat(iso)


def days_to_expiry(expire: Any, *, as_of: date | None = None) -> int | None:
    expire_date = _as_date(expire)
    if expire_date is None:
        return None
    today = as_of or date.today()
    return (expire_date - today).days


def _normalize_underlying(raw: str) -> str:
    text = str(raw or "").strip().upper().replace(" ", "")
    if "." in text:
        text = text.split(".", 1)[0]
    if text.endswith("ETF"):
        text = text[:-3]
    return text


def _underlying_matches(item: Mapping[str, Any], wanted: str) -> bool:
    if not wanted:
        return True
    candidates = [
        item.get("underlying"),
        item.get("product_id"),
        item.get("symbol"),
    ]
    wanted_n = _normalize_underlying(wanted)
    for candidate in candidates:
        cand = _normalize_underlying(str(candidate or ""))
        if cand and (cand == wanted_n or cand.startswith(wanted_n) or wanted_n.startswith(cand)):
            return True
    name = str(item.get("name") or "")
    return wanted_n in name.upper()


def _normalize_side(value: str | None) -> str | None:
    text = str(value or "").strip().upper()
    if not text:
        return None
    if text in {"C", "CALL", "购", "认购"}:
        return "C"
    if text in {"P", "PUT", "沽", "认沽"}:
        return "P"
    return None


def _closes_from_klines(rows: Sequence[Mapping[str, Any]] | None) -> List[float]:
    closes: List[float] = []
    for row in rows or []:
        if not isinstance(row, Mapping):
            continue
        value = row.get("close")
        if value is None:
            value = row.get("c") or row.get("Close")
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number > 0:
            closes.append(number)
    return closes


def _spot_and_sigma(
    *,
    underlying: str,
    kind: str,
    kline_loader: Callable[..., Any] | None,
) -> tuple[float | None, float, str]:
    if kline_loader is None:
        return None, _DEFAULT_SIGMA, "default"
    market = "CNStock"
    symbol = underlying
    if kind == "etf" or (underlying and len(_normalize_underlying(underlying)) == 6 and _normalize_underlying(underlying).isdigit()):
        symbol = cn_etf_stock_symbol(_normalize_underlying(underlying))
        market = "CNStock"
    try:
        rows = kline_loader(market=market, symbol=symbol, timeframe="1D", limit=60) or []
    except Exception as exc:
        logger.warning("option chain kline failed %s %s: %s", market, symbol, exc)
        return None, _DEFAULT_SIGMA, "default"
    closes = _closes_from_klines(rows)
    if not closes:
        return None, _DEFAULT_SIGMA, "default"
    sigma = realized_vol_from_closes(closes, window=20) or _DEFAULT_SIGMA
    return closes[-1], max(float(sigma), 0.05), "realized_vol"


def _contract_greeks(
    item: Mapping[str, Any],
    *,
    spot: float | None,
    sigma: float,
    as_of: date,
    rate: float,
) -> dict[str, Any] | None:
    strike = align_strike_to_spot(spot, item.get("strike") if isinstance(item.get("strike"), (int, float)) else None)
    if strike is None:
        try:
            strike = align_strike_to_spot(spot, float(item.get("strike")))
        except (TypeError, ValueError):
            strike = None
    dte = days_to_expiry(item.get("expire_date") or item.get("expire"), as_of=as_of)
    call_put = str(item.get("call_put") or "").upper()
    if spot is None or strike is None or dte is None or call_put not in {"C", "P"}:
        return None
    if dte < 0:
        return None
    model = "bs" if item.get("kind") == "etf" else "black76"
    return black_scholes_greeks(
        spot=float(spot),
        strike=float(strike),
        tte=max(dte, 0) / 365.0,
        sigma=float(sigma),
        is_call=call_put == "C",
        rate=rate,
        model=model,
    )


def query_option_chain(
    *,
    underlying: str,
    dte_min: int | None = None,
    dte_max: int | None = None,
    delta_min: float | None = None,
    delta_max: float | None = None,
    side: str | None = None,
    target_dte: int | None = None,
    target_delta: float | None = None,
    kind: str | None = "etf",
    limit: int = 40,
    as_of: date | None = None,
    catalog: Optional[Sequence[Mapping[str, Any]]] = None,
    kline_loader: Callable[..., Any] | None = None,
    rate: float = _DEFAULT_RATE,
) -> dict[str, Any]:
    """Return listed contracts matching DTE / delta filters, ranked for leg selection."""
    wanted = _normalize_underlying(underlying)
    if not wanted:
        raise ValueError("underlying is required")
    as_of = as_of or date.today()
    side_n = _normalize_side(side)
    kind_n = str(kind or "").strip().lower() or None
    rows = list(catalog) if catalog is not None else listed_option_catalog()
    spot, sigma, vol_source = _spot_and_sigma(
        underlying=wanted,
        kind=kind_n or "etf",
        kline_loader=kline_loader,
    )

    selected: List[Dict[str, Any]] = []
    for item in rows:
        if kind_n and str(item.get("kind") or "").lower() != kind_n:
            continue
        if not _underlying_matches(item, wanted):
            continue
        dte = days_to_expiry(item.get("expire_date") or item.get("expire"), as_of=as_of)
        if dte_min is not None and (dte is None or dte < dte_min):
            continue
        if dte_max is not None and (dte is None or dte > dte_max):
            continue
        call_put = str(item.get("call_put") or "").upper()
        if side_n and call_put != side_n:
            continue
        greeks = _contract_greeks(item, spot=spot, sigma=sigma, as_of=as_of, rate=rate)
        delta = None if greeks is None else float(greeks["delta"])
        if delta_min is not None and (delta is None or delta < delta_min):
            continue
        if delta_max is not None and (delta is None or delta > delta_max):
            continue
        strike = item.get("strike")
        aligned = align_strike_to_spot(spot, float(strike) if strike is not None else None)
        score = 0.0
        if target_dte is not None and dte is not None:
            score += abs(dte - target_dte) / 30.0
        elif target_dte is not None:
            score += 10.0
        if target_delta is not None and delta is not None:
            score += abs(delta - target_delta)
        elif target_delta is not None:
            score += 10.0
        selected.append(
            {
                "market": item.get("market") or "CNIndexOptions",
                "symbol": item.get("symbol"),
                "name": item.get("name"),
                "exchange": item.get("exchange"),
                "underlying": item.get("underlying") or wanted,
                "kind": item.get("kind"),
                "call_put": call_put or None,
                "strike": aligned if aligned is not None else strike,
                "expire": item.get("expire"),
                "expire_date": item.get("expire_date"),
                "dte": dte,
                "multiplier": item.get("lot_size") or 10000.0,
                "tick_size": item.get("tick_size"),
                "delta": delta,
                "gamma": None if greeks is None else greeks["gamma"],
                "vega": None if greeks is None else greeks["vega"],
                "theta": None if greeks is None else greeks["theta"],
                "theoretical": None if greeks is None else greeks["price"],
                "score": score,
            }
        )

    selected.sort(
        key=lambda row: (
            float(row.get("score") or 0.0),
            abs(int(row.get("dte") or 0) - int(target_dte or row.get("dte") or 0)),
            str(row.get("expire_date") or ""),
            float(row.get("strike") or 0.0),
        )
    )
    limit_n = max(1, min(200, int(limit or 40)))
    return {
        "underlying": wanted,
        "spot": spot,
        "sigma": sigma,
        "vol_source": vol_source,
        "as_of": as_of.isoformat(),
        "count": min(len(selected), limit_n),
        "total_matched": len(selected),
        "contracts": selected[:limit_n],
    }


def catalog_by_symbol(
    symbols: Iterable[str],
    *,
    catalog: Optional[Sequence[Mapping[str, Any]]] = None,
) -> Dict[str, Mapping[str, Any]]:
    wanted = {str(symbol).strip() for symbol in symbols if str(symbol).strip()}
    rows = list(catalog) if catalog is not None else listed_option_catalog()
    found: Dict[str, Mapping[str, Any]] = {}
    for item in rows:
        symbol = str(item.get("symbol") or "").strip()
        instrument = str(item.get("instrument_id") or "").strip()
        if symbol in wanted:
            found[symbol] = item
        if instrument and instrument in wanted and instrument not in found:
            found[instrument] = item
    return found

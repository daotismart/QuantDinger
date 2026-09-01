"""Normalize backtest results into chart-ready decision / fill / position series."""

from __future__ import annotations

from typing import Any


def build_backtest_visualization(result: dict[str, Any] | None) -> dict[str, Any]:
    payload = result if isinstance(result, dict) else {}
    decisions = _decision_process(payload)
    fills = _fill_series(payload)
    positions = _position_series(payload)
    return {
        "decisionProcess": decisions,
        "fills": fills,
        "positions": positions,
        "summaries": {
            "decisionCounts": _count_by(decisions, "kind"),
            "fillSides": _count_by(fills, "side"),
            "fillStatuses": _count_by(fills, "status"),
            "symbolCount": len({str(row.get("symbol") or "") for row in positions if row.get("symbol")}),
            "decisionCount": len(decisions),
            "fillCount": len(fills),
            "positionPointCount": len(positions),
        },
    }


def _decision_process(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in _list(result.get("protectionEvents")):
        rows.append(
            _event(
                time=_time(item.get("time")),
                kind="protect",
                symbol=item.get("symbol"),
                side=item.get("side"),
                reason=item.get("reason"),
                label=str(item.get("reason") or "protection"),
                value=_number(item.get("triggerPrice") or item.get("fillReferencePrice")),
            )
        )
    for item in _list(result.get("rebalanceRecords")):
        rows.append(
            _event(
                time=_time(item.get("time")),
                kind="rebalance",
                symbol="",
                side="",
                reason="rebalance",
                label=f"rebalance filled={item.get('filled') or 0}",
                value=_number(item.get("turnover")),
            )
        )
    for item in _list(result.get("orderLedger")):
        status = str(item.get("status") or "").strip().lower()
        reason = str(item.get("statusReason") or item.get("reason") or status)
        if status in {"rejected", "deferred", "partial"}:
            rows.append(
                _event(
                    time=_time(item.get("eventTime") or item.get("time")),
                    kind=status,
                    symbol=item.get("symbol"),
                    side=item.get("side"),
                    reason=reason,
                    label=reason or status,
                    value=_number(item.get("filledQuantity") or item.get("requestedQuantity")),
                )
            )
    for item in _list(result.get("closedTrades") or result.get("trades")):
        rows.append(
            _event(
                time=_time(item.get("entry_time") or item.get("entryDate")),
                kind="enter",
                symbol=item.get("symbol"),
                side=item.get("side"),
                reason=item.get("structure") or "entry",
                label="entry",
                value=_number(item.get("entry_price") or item.get("entryCredit")),
            )
        )
        rows.append(
            _event(
                time=_time(item.get("exit_time") or item.get("exitDate")),
                kind="exit",
                symbol=item.get("symbol"),
                side=item.get("side"),
                reason=item.get("close_reason") or item.get("reason"),
                label=str(item.get("close_reason") or item.get("reason") or "exit"),
                value=_number(item.get("profit") or item.get("pnl")),
            )
        )
    for line in _list(result.get("logs")):
        text = str(line or "").strip()
        if not text:
            continue
        lowered = text.lower()
        if any(token in lowered for token in ("enter", "exit", "reject", "protect", "order", "signal")):
            rows.append(_event(time="", kind="log", symbol="", side="", reason=text, label=text[:48], value=0.0))
    rows = [row for row in rows if row.get("time") or row.get("kind") == "log"]
    rows.sort(key=lambda row: (str(row.get("time") or ""), str(row.get("kind") or "")))
    return rows


def _fill_series(result: dict[str, Any]) -> list[dict[str, Any]]:
    executions = [
        item
        for item in _list(result.get("executions") or result.get("rawTrades"))
        if isinstance(item, dict)
    ]
    if not executions:
        for item in _list(result.get("orderLedger")):
            if str(item.get("status") or "").strip().lower() != "filled":
                continue
            qty = abs(_number(item.get("filledQuantity") or item.get("requestedQuantity")))
            price = _number(item.get("price"))
            executions.append(
                {
                    "time": item.get("eventTime") or item.get("time"),
                    "symbol": item.get("symbol"),
                    "side": item.get("side") or ("buy" if qty > 0 else "sell"),
                    "quantity": qty,
                    "price": price,
                    "notional": qty * price,
                    "commission": _number(item.get("commission")),
                    "status": "filled",
                    "reason": item.get("statusReason") or item.get("reason"),
                }
            )
    if not executions:
        for trade in _list(result.get("closedTrades") or result.get("trades")):
            qty = abs(_number(trade.get("quantity") or trade.get("amount") or 1))
            executions.append(
                {
                    "time": trade.get("entry_time") or trade.get("entryDate"),
                    "symbol": trade.get("symbol"),
                    "side": "sell" if str(trade.get("side") or "").lower() == "short" else "buy",
                    "quantity": qty,
                    "price": _number(trade.get("entry_price") or trade.get("entryCredit")),
                    "notional": qty * abs(_number(trade.get("entry_price") or trade.get("entryCredit"))),
                    "commission": _number(trade.get("entry_commission") or trade.get("commission") or trade.get("fees")) / 2.0,
                    "status": "filled",
                    "reason": "entry",
                    "profit": 0.0,
                }
            )
            executions.append(
                {
                    "time": trade.get("exit_time") or trade.get("exitDate"),
                    "symbol": trade.get("symbol"),
                    "side": "buy" if str(trade.get("side") or "").lower() == "short" else "sell",
                    "quantity": qty,
                    "price": _number(trade.get("exit_price") or trade.get("exitDebit")),
                    "notional": qty * abs(_number(trade.get("exit_price") or trade.get("exitDebit"))),
                    "commission": _number(trade.get("exit_commission") or trade.get("commission") or trade.get("fees")) / 2.0,
                    "status": "filled",
                    "reason": trade.get("close_reason") or trade.get("reason") or "exit",
                    "profit": _number(trade.get("profit") or trade.get("pnl")),
                }
            )

    rows: list[dict[str, Any]] = []
    cumulative = 0.0
    for item in sorted(executions, key=lambda row: _time(row.get("time") or row.get("signal_time"))):
        qty = abs(_number(item.get("quantity") or item.get("filledQuantity") or item.get("amount")))
        price = _number(item.get("price") or item.get("exit_price"))
        notional = _number(item.get("notional"))
        if notional == 0.0:
            notional = qty * price
        pnl = _number(item.get("profit") or item.get("gross_profit"))
        cumulative += pnl
        side = str(item.get("side") or "").strip().lower()
        if side not in {"buy", "sell", "long", "short"}:
            side = "buy" if qty >= 0 else "sell"
        if side == "long":
            side = "buy"
        if side == "short":
            side = "sell"
        rows.append(
            {
                "time": _time(item.get("time") or item.get("signal_time")),
                "symbol": str(item.get("symbol") or item.get("position_key") or ""),
                "side": side,
                "quantity": qty,
                "price": price,
                "notional": notional,
                "commission": _number(item.get("commission")),
                "status": str(item.get("status") or "filled"),
                "reason": str(item.get("reason") or item.get("close_reason") or ""),
                "cumulativePnl": cumulative,
            }
        )
    return [row for row in rows if row.get("time")]


def _position_series(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for snapshot in _list(result.get("holdingSnapshots")):
        time = _time(snapshot.get("time"))
        positions = snapshot.get("positions") if isinstance(snapshot.get("positions"), dict) else {}
        if not positions:
            rows.append(
                {
                    "time": time,
                    "symbol": "",
                    "quantity": 0.0,
                    "marketValue": 0.0,
                    "weight": 0.0,
                    "averageCost": 0.0,
                    "cash": _number(snapshot.get("cash")),
                    "grossExposure": _number(snapshot.get("grossExposure")),
                    "netExposure": _number(snapshot.get("netExposure")),
                }
            )
            continue
        for symbol, position in positions.items():
            pos = position if isinstance(position, dict) else {}
            rows.append(
                {
                    "time": time,
                    "symbol": str(symbol),
                    "quantity": _number(pos.get("quantity") or pos.get("amount")),
                    "marketValue": _number(pos.get("marketValue")),
                    "weight": _number(pos.get("weight")),
                    "averageCost": _number(pos.get("averageCost") or pos.get("avgCost")),
                    "cash": _number(snapshot.get("cash")),
                    "grossExposure": _number(snapshot.get("grossExposure")),
                    "netExposure": _number(snapshot.get("netExposure")),
                }
            )
    if rows:
        return rows

    curve = [item for item in _list(result.get("equityCurve")) if isinstance(item, dict)]
    trades = [item for item in _list(result.get("closedTrades") or result.get("trades")) if isinstance(item, dict)]
    if not curve:
        return []
    symbol = str((trades[0] or {}).get("symbol") or "") if trades else ""
    ordered = sorted(trades, key=lambda item: _time(item.get("entry_time") or item.get("entryDate")))
    for point in curve:
        time = _time(point.get("time") or point.get("date"))
        still_open = 0.0
        for trade in ordered:
            entry = _time(trade.get("entry_time") or trade.get("entryDate"))
            exit_time = _time(trade.get("exit_time") or trade.get("exitDate"))
            if entry and entry <= time and (not exit_time or exit_time > time):
                still_open += abs(_number(trade.get("quantity") or trade.get("amount") or 1))
        value = _number(point.get("value") or point.get("equity"))
        cash = _number(point.get("cash") if point.get("cash") is not None else value)
        rows.append(
            {
                "time": time,
                "symbol": symbol,
                "quantity": still_open,
                "marketValue": max(value - cash, 0.0),
                "weight": (value - cash) / value if value else 0.0,
                "averageCost": 0.0,
                "cash": cash,
                "grossExposure": _number(point.get("grossExposure")),
                "netExposure": _number(point.get("netExposure")),
            }
        )
    return rows


def _event(**kwargs: Any) -> dict[str, Any]:
    return {
        "time": kwargs.get("time") or "",
        "kind": str(kwargs.get("kind") or ""),
        "symbol": str(kwargs.get("symbol") or ""),
        "side": str(kwargs.get("side") or ""),
        "reason": str(kwargs.get("reason") or ""),
        "label": str(kwargs.get("label") or kwargs.get("reason") or kwargs.get("kind") or ""),
        "value": _number(kwargs.get("value")),
    }


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _time(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if "T" not in text and len(text) >= 10:
        return f"{text[:10]}T16:00:00Z"
    return text


def _count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        name = str(row.get(key) or "unknown")
        counts[name] = counts.get(name, 0) + 1
    return counts

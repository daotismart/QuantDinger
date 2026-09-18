"""Coerce strategy/indicator parameter values into round()-safe Python scalars.

JSON cannot carry ``complex``, but `# @param` defaults and UI rewrites can still
land as strings such as ``7j`` (Python imaginary suffix) or numpy scalars.
``round(7j)`` raises ``type complex doesn't define __round__ method``.
"""

from __future__ import annotations

import math
import re
from typing import Any

_INT_RE = re.compile(r"^[+-]?\d+$")
_FLOAT_RE = re.compile(r"^[+-]?(?:\d+\.\d*|\.\d+)$")
_SCI_RE = re.compile(r"^[+-]?\d+(?:\.\d+)?[eE][+-]?\d+$")
_IMAG_RE = re.compile(r"^([+-]?\d+(?:\.\d+)?)[jJ]$")
_YEAR_DATE_RE = re.compile(r"^(\d{4})[-/]\d{1,2}(?:[-/]\d{1,2})?$")


def coerce_param_value(raw: Any, declared_type: str | None = None) -> Any:
    """Convert ``raw`` to the declared param type, never leaving a complex."""
    value = _unwrap(raw)
    ptype = str(declared_type or "").strip().lower()
    if ptype in {"string", "str"}:
        return "" if value is None else str(value)
    if ptype in {"bool", "boolean"}:
        return _as_bool(value)
    if ptype == "int":
        return int(round(_as_real(value)))
    if ptype == "float":
        return float(_as_real(value))
    return _coerce_undeclared(value)


def safe_round(number: Any, ndigits: Any = None) -> Any:
    """Builtin-compatible ``round`` that unwraps complex / numpy scalars.

    ``round(7j)`` raises ``TypeError: type complex doesn't define __round__
    method``. Strategy code often writes ``int(round(context.params.get(..., 7j)))``
    as a fallback; the sandbox must not crash when that default is hit.
    """
    try:
        real = _as_real(number)
    except (TypeError, ValueError, OverflowError):
        if ndigits is None:
            return round(number)
        return round(number, ndigits)
    if ndigits is None:
        return round(real)
    try:
        if isinstance(ndigits, bool) or not isinstance(ndigits, int):
            digits = int(_as_real(ndigits))
        else:
            digits = ndigits
    except (TypeError, ValueError, OverflowError):
        return round(real, ndigits)
    return round(real, digits)


def merge_declared_params(source: str, user_params: dict[str, Any] | None) -> dict[str, Any]:
    """Merge `# @param` defaults with run-supplied values and coerce types."""
    from app.services.indicator_params import IndicatorParamsParser

    declared = IndicatorParamsParser.parse_params(source or "")
    result: dict[str, Any] = dict(user_params or {})
    declared_names = set()
    for param in declared:
        name = str(param.get("name") or "").strip()
        if not name:
            continue
        declared_names.add(name)
        ptype = str(param.get("type") or "").strip().lower()
        if name in result:
            result[name] = coerce_param_value(result[name], ptype)
        else:
            result[name] = coerce_param_value(param.get("default"), ptype)
    for name, value in list(result.items()):
        if name not in declared_names:
            result[name] = coerce_param_value(value, None)
    return result


def _coerce_undeclared(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, complex):
        number = _complex_to_real(value)
        return int(number) if float(number).is_integer() else float(number)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isfinite(value) and value.is_integer():
            return int(value)
        return value
    if isinstance(value, str):
        parsed = _try_parse_number(value.strip())
        if parsed is None:
            return value
        if isinstance(parsed, float) and parsed.is_integer():
            return int(parsed)
        return parsed
    return value


def _unwrap(value: Any) -> Any:
    item = getattr(value, "item", None)
    if callable(item) and not isinstance(value, (bytes, str, dict, list, tuple)):
        try:
            value = item()
        except Exception:
            pass
    return value


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return bool(value)
    text = str(value or "").strip().lower()
    return text in {"true", "1", "yes", "on"}


def _as_real(value: Any) -> float:
    value = _unwrap(value)
    if value is None or value == "":
        raise TypeError("empty parameter value")
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, complex):
        return _complex_to_real(value)
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number):
            raise TypeError("non-finite parameter value")
        return number
    if isinstance(value, str):
        parsed = _try_parse_number(value.strip())
        if parsed is not None:
            return float(parsed)
    imag = getattr(value, "imag", None)
    real = getattr(value, "real", None)
    if imag is not None and real is not None and not isinstance(value, (bytes, str)):
        try:
            return _complex_to_real(complex(float(real), float(imag)))
        except Exception:
            pass
    raise TypeError(f"parameter value is not numeric: {value!r}")


def _complex_to_real(value: complex) -> float:
    if abs(value.imag) < 1e-12:
        return float(value.real)
    if abs(value.real) < 1e-12:
        # Python imaginary-suffix artifact: ``7j`` means 7, not 0+7j finance data.
        return float(value.imag)
    return float(value.real)


def _try_parse_number(text: str) -> int | float | None:
    if not text:
        return None
    if _INT_RE.fullmatch(text):
        return int(text)
    if _FLOAT_RE.fullmatch(text) or _SCI_RE.fullmatch(text):
        return float(text)
    imag = _IMAG_RE.fullmatch(text)
    if imag:
        return float(imag.group(1))
    year = _YEAR_DATE_RE.fullmatch(text)
    if year:
        return int(year.group(1))
    return None

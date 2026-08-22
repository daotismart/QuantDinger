"""Human-readable labels for Strategy API V2 sources and backtests."""

from __future__ import annotations

import re
from typing import Any, Mapping

_AUTO_NAME_PATTERN = re.compile(
    r"^\[(?:AUTO-BT\d*|PR14-BT|FIX-BT|UNIFIED)\].*|template_(?:None|\d+)|^Untitled Script$",
    re.IGNORECASE,
)
_DOC_TITLE_PATTERN = re.compile(r'\s*(?:"""|\'\'\')(.*?)(?:"""|\'\'\')', re.DOTALL)


def extract_code_doc_title(code: str) -> str:
    match = _DOC_TITLE_PATTERN.match(str(code or ""))
    if not match:
        return ""
    for line in str(match.group(1) or "").splitlines():
        cleaned = line.strip()
        if cleaned and not cleaned.startswith("# @param"):
            return cleaned
    return ""


def is_auto_generated_strategy_name(name: str) -> bool:
    raw = str(name or "").strip()
    if not raw:
        return True
    return bool(_AUTO_NAME_PATTERN.search(raw))


def format_universe_symbol(
    *,
    instruments: list[Mapping[str, Any]] | None = None,
    fallback_symbol: str = "",
    universe_reference: str = "",
    max_length: int = 50,
) -> str:
    if universe_reference:
        label = f"universe:{universe_reference}"
        return label[:max_length] if max_length > 0 else label
    items = [item for item in (instruments or []) if isinstance(item, Mapping)]
    if not items:
        raw = str(fallback_symbol or "").strip()
        if raw.startswith("basket:"):
            try:
                count = int(raw.split(":", 1)[1])
                raw = f"{count}-symbol basket"
            except (TypeError, ValueError):
                pass
        return raw[:max_length] if max_length > 0 else raw
    if len(items) == 1:
        symbol = str(items[0].get("symbol") or "").strip()
        market = str(items[0].get("market") or "").strip()
        label = f"{market}:{symbol}" if market and symbol else symbol or str(fallback_symbol or "").strip()
        return label[:max_length] if max_length > 0 else label
    short_symbols = [str(item.get("symbol") or "").strip() for item in items if str(item.get("symbol") or "").strip()]
    if short_symbols:
        label = " + ".join(short_symbols)
    else:
        labels: list[str] = []
        for item in items:
            symbol = str(item.get("symbol") or "").strip()
            market = str(item.get("market") or "").strip()
            if market and symbol:
                labels.append(f"{market}:{symbol}")
            elif symbol:
                labels.append(symbol)
        label = " + ".join(labels)
    if max_length > 0 and len(label) > max_length:
        return label[: max(1, max_length - 1)].rstrip() + "…"
    return label


def variant_label_from_metadata(metadata: Mapping[str, Any] | None, variant: Any) -> str:
    if variant is None:
        return ""
    try:
        index = int(variant)
    except (TypeError, ValueError):
        return str(variant)
    labels = (metadata or {}).get("variant_labels")
    if isinstance(labels, list) and 0 <= index < len(labels):
        label = str(labels[index] or "").strip()
        if label:
            return label
    return f"Variant {index + 1}"


def compose_strategy_display_name(
    *,
    name: str = "",
    code: str = "",
    template_title: str = "",
    template_key: str = "",
    params: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
    symbol: str = "",
    instruments: list[Mapping[str, Any]] | None = None,
    universe_reference: str = "",
) -> str:
    base = str(name or "").strip()
    if is_auto_generated_strategy_name(base):
        base = ""
    if not base:
        base = str(template_title or "").strip()
    if not base:
        base = extract_code_doc_title(code)
    if not base and template_key:
        base = template_key.removeprefix("strategy_v2_").replace("_", " ").strip().title()
    if not base:
        base = format_universe_symbol(
            instruments=instruments,
            fallback_symbol=symbol,
            universe_reference=universe_reference,
        )
    if not base:
        base = "Strategy"

    variant = (params or {}).get("variant")
    if variant is not None and str(variant).strip() != "":
        variant_text = variant_label_from_metadata(metadata, variant)
        base = re.sub(r"\s*variant\s*\d+\s*$", "", base, flags=re.IGNORECASE).strip()
        lowered = base.lower()
        if variant_text.lower() not in lowered:
            base = f"{base} · {variant_text}"
    return base


def resolve_template_title(template_key: str, templates_by_key: Mapping[str, Mapping[str, Any]]) -> str:
    key = str(template_key or "").strip()
    if not key:
        return ""
    row = templates_by_key.get(key)
    if not isinstance(row, Mapping):
        return ""
    return str(row.get("title") or "").strip()

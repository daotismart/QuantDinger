"""Load historical ETF option chains for listed-strike iron-condor research.

Prefers the local etf_options ClickHouse service (daily analytics + contract
meta + 1m open interest). Falls back to CSV dumps under ``GEX_LSP_DATA_DIR``.
"""

from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from app.utils.logger import get_logger

logger = get_logger(__name__)

_NAME_RE = re.compile(r"(购|沽)\s*(\d{1,2})\s*月\s*(\d+)\s*(A)?\s*$")
_DEFAULT_CH_URL = "http://172.17.0.1:18123"
_DEFAULT_CH_DB = "etf_options"
_DEFAULT_CSV_DIR = Path("tmp/gex_lsp_strangle")


def etf_options_ch_url() -> str:
    return (
        os.getenv("ETF_OPTIONS_CH_URL")
        or os.getenv("CLICKHOUSE_HTTP_URL")
        or _DEFAULT_CH_URL
    ).rstrip("/")


def etf_options_ch_database() -> str:
    return (
        os.getenv("ETF_OPTIONS_CH_DATABASE")
        or os.getenv("CLICKHOUSE_DATABASE")
        or _DEFAULT_CH_DB
    ).strip() or _DEFAULT_CH_DB


def etf_options_ch_enabled() -> bool:
    raw = os.getenv("ETF_OPTIONS_CH_ENABLED", "true").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def csv_data_dir() -> Path:
    raw = os.getenv("GEX_LSP_DATA_DIR") or str(_DEFAULT_CSV_DIR)
    return Path(raw)


def sanitize_underlying_code(code: object) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z.]", "", str(code or ""))
    return cleaned or "510050"


def fourth_wednesday(year: int, month: int) -> date:
    first = date(year, month, 1)
    offset = (2 - first.weekday()) % 7
    return first + timedelta(days=offset + 21)


def parse_etf_option_display_name(name: object, *, asof: Any | None = None) -> dict[str, Any] | None:
    """Parse ``50ETF购9月3100`` / ``50ETF沽6月3215A`` display names."""
    raw = str(name or "").strip()
    match = _NAME_RE.search(raw)
    if not match:
        return None
    cp = "C" if match.group(1) == "购" else "P"
    month = int(match.group(2))
    strike_raw = int(match.group(3))
    strike = strike_raw / 1000.0 if strike_raw >= 200 else float(strike_raw)
    asof_ts = pd.to_datetime(asof, errors="coerce") if asof is not None else pd.NaT
    year = int(asof_ts.year) if pd.notna(asof_ts) else date.today().year
    if pd.notna(asof_ts) and month < int(asof_ts.month):
        year += 1
    return {
        "contract_code": raw,
        "cp": cp,
        "strike": strike,
        "expire_date": pd.Timestamp(fourth_wednesday(year, month)),
        "adjusted": bool(match.group(4)),
    }


def complete_chain_metadata(chain: pd.DataFrame) -> pd.DataFrame:
    """Fill strike / cp / expiry from display names when the catalog join misses."""
    if chain is None or chain.empty:
        return pd.DataFrame()
    out = chain.copy()
    out["contract_code"] = out["contract_code"].astype(str).str.strip()
    out["trade_date"] = pd.to_datetime(out["trade_date"], errors="coerce")
    out["strike"] = pd.to_numeric(out.get("strike"), errors="coerce")
    out["cp"] = out.get("cp", "").astype(str).str.strip().str.upper().str[:1]
    out.loc[~out["cp"].isin(["C", "P"]), "cp"] = ""
    expire = pd.to_datetime(out.get("expire_date"), errors="coerce")
    out["expire_date"] = expire

    known = (
        out[out["cp"].isin(["C", "P"]) & out["strike"].fillna(0).gt(0) & out["expire_date"].notna()]
        .sort_values("trade_date")
        .drop_duplicates("contract_code", keep="last")
        .set_index("contract_code")[["strike", "cp", "expire_date"]]
    )
    parsed_rows = []
    for idx, row in out.iterrows():
        need = (row.get("cp") not in {"C", "P"}) or (not (row.get("strike") or 0) > 0) or pd.isna(row.get("expire_date"))
        if not need:
            continue
        code = str(row.get("contract_code") or "")
        if code in known.index:
            hit = known.loc[code]
            out.at[idx, "strike"] = float(hit["strike"])
            out.at[idx, "cp"] = str(hit["cp"])
            out.at[idx, "expire_date"] = hit["expire_date"]
            continue
        parsed = parse_etf_option_display_name(code, asof=row.get("trade_date"))
        if parsed is None:
            continue
        parsed_rows.append(idx)
        out.at[idx, "strike"] = parsed["strike"]
        out.at[idx, "cp"] = parsed["cp"]
        if pd.isna(out.at[idx, "expire_date"]):
            out.at[idx, "expire_date"] = parsed["expire_date"]
    out = out[out["cp"].isin(["C", "P"]) & out["strike"].fillna(0).gt(0) & out["expire_date"].notna()]
    return out.reset_index(drop=True)


def attach_open_interest(chain: pd.DataFrame, oi: pd.DataFrame) -> pd.DataFrame:
    if chain is None or chain.empty:
        return pd.DataFrame()
    out = chain.copy()
    out["contract_code"] = out["contract_code"].astype(str).str.strip()
    out["trade_date"] = pd.to_datetime(out["trade_date"], errors="coerce")
    if oi is None or oi.empty:
        out["open_interest"] = 0.0
        return out
    oi_df = oi.copy()
    oi_df["contract_code"] = oi_df["contract_code"].astype(str).str.strip()
    oi_df["trade_date"] = pd.to_datetime(oi_df["trade_date"], errors="coerce")
    oi_df["open_interest"] = pd.to_numeric(oi_df.get("open_interest"), errors="coerce")
    oi_df = oi_df.dropna(subset=["trade_date", "contract_code"])
    merged = out.merge(
        oi_df[["trade_date", "contract_code", "open_interest"]],
        on=["trade_date", "contract_code"],
        how="left",
    )
    merged = merged.sort_values(["contract_code", "trade_date"])
    grouped = merged.groupby("contract_code")["open_interest"]
    merged["open_interest"] = grouped.ffill()
    merged["open_interest"] = merged.groupby("contract_code")["open_interest"].bfill()
    merged["open_interest"] = merged["open_interest"].fillna(0.0)
    return merged.reset_index(drop=True)


def _ch_query(sql: str, *, timeout: float = 120.0) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode(
        {
            "database": etf_options_ch_database(),
            "default_format": "JSONEachRow",
        }
    )
    url = f"{etf_options_ch_url()}/?{params}"
    req = urllib.request.Request(
        url,
        data=sql.encode("utf-8"),
        method="POST",
        headers={"Content-Type": "text/plain; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        text = resp.read().decode("utf-8")
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def load_from_clickhouse(
    underlying: str,
    *,
    start: Any | None = None,
    end: Any | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    code = sanitize_underlying_code(underlying)
    start_sql = pd.Timestamp(start).date().isoformat() if start is not None else "1970-01-01"
    end_sql = pd.Timestamp(end).date().isoformat() if end is not None else "2100-01-01"
    chain_sql = f"""
        SELECT
          a.trade_date,
          trimBoth(a.underlying_code) AS underlying_code,
          trimBoth(a.contract_code) AS contract_code,
          c.strike,
          c.cp,
          c.expire_date,
          a.option_close,
          a.underlying_close,
          a.delta,
          a.gamma,
          a.vega,
          a.theta,
          a.iv
        FROM opt_analytics_daily AS a
        LEFT JOIN
        (
          SELECT
            trade_date,
            trimBoth(underlying_code) AS underlying_code,
            trimBoth(contract_code) AS contract_code,
            anyLast(strike) AS strike,
            anyLast(cp) AS cp,
            anyLast(expire_date) AS expire_date
          FROM opt_contracts_daily
          WHERE trimBoth(underlying_code) = '{code}'
            AND trade_date >= '{start_sql}'
            AND trade_date <= '{end_sql}'
          GROUP BY trade_date, underlying_code, contract_code
        ) AS c
          ON a.trade_date = c.trade_date
         AND trimBoth(a.underlying_code) = c.underlying_code
         AND trimBoth(a.contract_code) = c.contract_code
        WHERE trimBoth(a.underlying_code) = '{code}'
          AND a.trade_date >= '{start_sql}'
          AND a.trade_date <= '{end_sql}'
        ORDER BY a.trade_date, c.expire_date, c.cp, c.strike
    """
    oi_sql = f"""
        SELECT
          toDate(ts_minute) AS trade_date,
          '{code}' AS underlying_code,
          trimBoth(contract_code) AS contract_code,
          argMax(open_interest, ts_minute) AS open_interest
        FROM opt_quotes_bar_1m
        WHERE trimBoth(underlying_code) = '{code}'
          AND toDate(ts_minute) >= '{start_sql}'
          AND toDate(ts_minute) <= '{end_sql}'
        GROUP BY trade_date, contract_code
        ORDER BY trade_date, contract_code
    """
    und_sql = f"""
        SELECT trade_date, underlying_code, open, high, low, close, volume, amount
        FROM opt_underlying_daily
        WHERE underlying_code = '{code}'
          AND trade_date >= '{start_sql}'
          AND trade_date <= '{end_sql}'
        ORDER BY trade_date
    """
    chain = pd.DataFrame(_ch_query(chain_sql))
    oi = pd.DataFrame(_ch_query(oi_sql))
    und = pd.DataFrame(_ch_query(und_sql))
    return und, chain, oi


def load_from_csv(
    underlying: str,
    *,
    data_dir: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    folder = Path(data_dir or csv_data_dir())
    code = sanitize_underlying_code(underlying)
    und = pd.read_csv(folder / f"underlying_{code}.csv")
    chain = pd.read_csv(folder / f"chain_{code}.csv")
    oi = pd.read_csv(folder / f"oi_{code}.csv")
    return und, chain, oi


def load_listed_option_panel(
    underlying: str = "510050",
    *,
    start: Any | None = None,
    end: Any | None = None,
    data_dir: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return ``(underlying, chain, oi)`` ready for ``run_iron_condor_backtest``."""
    code = sanitize_underlying_code(underlying)
    und = chain = oi = pd.DataFrame()
    if etf_options_ch_enabled():
        try:
            und, chain, oi = load_from_clickhouse(code, start=start, end=end)
            if chain is not None and not chain.empty:
                logger.info(
                    "iron-condor chain from ClickHouse underlying=%s rows=%s days=%s",
                    code,
                    len(chain),
                    pd.to_datetime(chain["trade_date"]).nunique() if "trade_date" in chain.columns else 0,
                )
        except Exception as exc:
            logger.warning("ClickHouse option chain load failed for %s: %s", code, exc)
    if chain is None or chain.empty:
        und, chain, oi = load_from_csv(code, data_dir=data_dir)
        logger.info(
            "iron-condor chain from CSV underlying=%s rows=%s dir=%s",
            code,
            len(chain),
            data_dir or csv_data_dir(),
        )
    chain = complete_chain_metadata(chain)
    chain = attach_open_interest(chain, oi)
    und = und.copy()
    und["trade_date"] = pd.to_datetime(und["trade_date"], errors="coerce")
    if start is not None:
        start_ts = pd.Timestamp(start).normalize()
        und = und[und["trade_date"] >= start_ts]
        chain = chain[chain["trade_date"] >= start_ts]
    if end is not None:
        end_ts = pd.Timestamp(end).normalize()
        und = und[und["trade_date"] <= end_ts]
        chain = chain[chain["trade_date"] <= end_ts]
    oi = chain[["trade_date", "underlying_code", "contract_code", "open_interest"]].copy()
    # prepare_panel merges OI itself; keep a single open_interest column.
    if "open_interest" in chain.columns:
        chain = chain.drop(columns=["open_interest"])
    if "underlying_code" not in und.columns:
        und["underlying_code"] = code
    return und.reset_index(drop=True), chain.reset_index(drop=True), oi.reset_index(drop=True)

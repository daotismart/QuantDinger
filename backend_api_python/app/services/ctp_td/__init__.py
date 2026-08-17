"""CTP TdApi trading integration (CN futures / futures options).

Requires ``CFFEX_LIVE_TRADING_ENABLED=true`` plus OpenCTP (or compatible)
TraderApi bindings. Market data remains in ``app.services.ctp_md``.
"""

from app.services.ctp_td.config import CtpTdSettings, cffex_live_trading_enabled, settings_from_mapping
from app.services.ctp_td.gateway import (
    CtpOrderFill,
    CtpTdDependencyError,
    CtpTdError,
    CtpTdGateway,
    format_instrument_id,
    get_ctp_td_gateway,
    load_ctp_tdapi,
    map_side_offset_to_ctp,
    signal_to_side_offset,
)

__all__ = [
    "CtpOrderFill",
    "CtpTdDependencyError",
    "CtpTdError",
    "CtpTdGateway",
    "CtpTdSettings",
    "cffex_live_trading_enabled",
    "format_instrument_id",
    "get_ctp_td_gateway",
    "load_ctp_tdapi",
    "map_side_offset_to_ctp",
    "settings_from_mapping",
    "signal_to_side_offset",
]

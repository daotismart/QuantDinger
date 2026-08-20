"""CTP TdApi (trading) configuration from env and credential overlays."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional


def _truthy(value: Optional[str]) -> bool:
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


def _env(name: str, default: str = "") -> str:
    return str(os.getenv(name, default) or "").strip()


def cffex_live_trading_enabled() -> bool:
    return _truthy(os.getenv("CFFEX_LIVE_TRADING_ENABLED"))


@dataclass(frozen=True)
class CtpTdSettings:
    """Connection settings for CTP TraderApi (order placement)."""

    enabled: bool
    front: str
    broker_id: str
    user_id: str
    password: str
    app_id: str
    auth_code: str
    product_info: str
    investor_id: str
    flow_path: str
    api_module: str
    order_timeout_sec: float
    reconnect_seconds: float

    @property
    def configured(self) -> bool:
        return bool(self.enabled and self.front and self.broker_id and self.user_id and self.password)


def settings_from_mapping(cfg: Optional[Dict[str, Any]] = None) -> CtpTdSettings:
    """Build TdApi settings from exchange_config with env fallbacks (CTP_TD_* / CTP_MD_*)."""
    raw = dict(cfg or {})

    def pick(*keys: str, env_keys: tuple[str, ...] = (), default: str = "") -> str:
        for key in keys:
            value = raw.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        for env_key in env_keys:
            value = _env(env_key)
            if value:
                return value
        return default

    front = pick(
        "td_front",
        "tdFront",
        "front",
        env_keys=("CTP_TD_FRONT", "CTP_MD_FRONT"),
    )
    if front and not front.lower().startswith("tcp://"):
        front = f"tcp://{front}"

    user_id = pick(
        "user_id",
        "userId",
        "api_key",
        env_keys=("CTP_TD_USER_ID", "CTP_MD_USER_ID"),
    )
    investor_id = pick(
        "investor_id",
        "investorId",
        env_keys=("CTP_TD_INVESTOR_ID",),
        default=user_id,
    )

    if raw.get("enabled") is not None:
        enabled = _truthy(str(raw.get("enabled")))
    else:
        # Separate from CFFEX_LIVE_TRADING_ENABLED (kill switch on CtpClient).
        enabled = _truthy(_env("CTP_TD_ENABLED", "true"))

    return CtpTdSettings(
        enabled=enabled,
        front=front,
        broker_id=pick(
            "broker_id",
            "brokerId",
            env_keys=("CTP_TD_BROKER_ID", "CTP_MD_BROKER_ID"),
        ),
        user_id=user_id,
        password=pick(
            "password",
            "secret_key",
            "secret",
            env_keys=("CTP_TD_PASSWORD", "CTP_MD_PASSWORD"),
        ),
        app_id=pick(
            "app_id",
            "appId",
            env_keys=("CTP_TD_APP_ID", "CTP_MD_APP_ID"),
        ),
        auth_code=pick(
            "auth_code",
            "authCode",
            env_keys=("CTP_TD_AUTH_CODE", "CTP_MD_AUTH_CODE"),
        ),
        product_info=pick(
            "product_info",
            "productInfo",
            "UserProductInfo",
            env_keys=("CTP_TD_PRODUCT_INFO", "CTP_MD_PRODUCT_INFO"),
        ),
        investor_id=investor_id or user_id,
        flow_path=pick(
            "flow_path",
            "flowPath",
            env_keys=("CTP_TD_FLOW_PATH",),
            default="/tmp/ctp_td_flow/",
        )
        or "/tmp/ctp_td_flow/",
        api_module=pick(
            "api_module",
            "apiModule",
            env_keys=("CTP_TD_API_MODULE", "CTP_MD_API_MODULE"),
            default="openctp_ctp",
        ),
        order_timeout_sec=max(
            1.0,
            float(
                raw.get("order_timeout_sec")
                or raw.get("orderTimeoutSec")
                or _env("CTP_TD_ORDER_TIMEOUT_SEC", "15")
                or 15
            ),
        ),
        reconnect_seconds=max(
            1.0,
            float(
                raw.get("reconnect_seconds")
                or _env("CTP_TD_RECONNECT_SECONDS", "5")
                or 5
            ),
        ),
    )

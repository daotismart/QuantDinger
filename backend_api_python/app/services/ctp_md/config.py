"""CTP market-data configuration from env / addon config."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

from app.config.data_sources import _config_int, _config_str


def _config_bool(section: str, key: str, env_name: str, default: bool = False) -> bool:
    from app.config.data_sources import _addon

    value = _addon(section, key)
    if value is None:
        value = os.getenv(env_name)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class CtpMdSettings:
    """Connection settings for CTP MdApi (market data only)."""

    enabled: bool
    front: str
    broker_id: str
    user_id: str
    password: str
    app_id: str
    auth_code: str
    product_info: str
    flow_path: str
    instruments: List[str]
    reconnect_seconds: float
    tick_stale_after_seconds: float

    @property
    def configured(self) -> bool:
        return bool(self.enabled and self.front and self.broker_id and self.user_id)


class MetaCtpMdConfig(type):
    @property
    def ENABLED(cls) -> bool:
        return _config_bool("ctp_md", "enabled", "CTP_MD_ENABLED", False)

    @property
    def FRONT(cls) -> str:
        # Default empty: operators must set a SimNow / broker Md front.
        return _config_str("ctp_md", "front", "CTP_MD_FRONT", "")

    @property
    def BROKER_ID(cls) -> str:
        return _config_str("ctp_md", "broker_id", "CTP_MD_BROKER_ID", "")

    @property
    def USER_ID(cls) -> str:
        return _config_str("ctp_md", "user_id", "CTP_MD_USER_ID", "")

    @property
    def PASSWORD(cls) -> str:
        return _config_str("ctp_md", "password", "CTP_MD_PASSWORD", "")

    @property
    def APP_ID(cls) -> str:
        return _config_str("ctp_md", "app_id", "CTP_MD_APP_ID", "")

    @property
    def AUTH_CODE(cls) -> str:
        return _config_str("ctp_md", "auth_code", "CTP_MD_AUTH_CODE", "")

    @property
    def PRODUCT_INFO(cls) -> str:
        # Broker-required UserProductInfo / ProductInfo (e.g. Zhongtai DTSCTP).
        return _config_str("ctp_md", "product_info", "CTP_MD_PRODUCT_INFO", "")

    @property
    def FLOW_PATH(cls) -> str:
        return _config_str("ctp_md", "flow_path", "CTP_MD_FLOW_PATH", "./ctp_md_flow/")

    @property
    def INSTRUMENTS(cls) -> List[str]:
        raw = _config_str("ctp_md", "instruments", "CTP_MD_INSTRUMENTS", "")
        return [item.strip() for item in raw.replace(";", ",").split(",") if item.strip()]

    @property
    def RECONNECT_SECONDS(cls) -> float:
        return float(_config_int("ctp_md", "reconnect_seconds", "CTP_MD_RECONNECT_SECONDS", 5))

    @property
    def TICK_STALE_AFTER_SECONDS(cls) -> float:
        return float(
            _config_int("ctp_md", "tick_stale_after_seconds", "CTP_MD_TICK_STALE_AFTER_SECONDS", 10)
        )


class CtpMdConfig(metaclass=MetaCtpMdConfig):
    """CTP market-data configuration accessors."""

    @classmethod
    def settings(cls) -> CtpMdSettings:
        return CtpMdSettings(
            enabled=bool(cls.ENABLED),
            front=str(cls.FRONT or "").strip(),
            broker_id=str(cls.BROKER_ID or "").strip(),
            user_id=str(cls.USER_ID or "").strip(),
            password=str(cls.PASSWORD or ""),
            app_id=str(cls.APP_ID or "").strip(),
            auth_code=str(cls.AUTH_CODE or "").strip(),
            product_info=str(cls.PRODUCT_INFO or "").strip(),
            flow_path=str(cls.FLOW_PATH or "./ctp_md_flow/").strip() or "./ctp_md_flow/",
            instruments=list(cls.INSTRUMENTS),
            reconnect_seconds=max(1.0, float(cls.RECONNECT_SECONDS or 5.0)),
            tick_stale_after_seconds=max(1.0, float(cls.TICK_STALE_AFTER_SECONDS or 10.0)),
        )

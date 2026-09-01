"""Runtime configuration for the local data service."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


@dataclass(frozen=True)
class LocalDataSettings:
    local_read_enabled: bool
    min_coverage: float
    max_stale_sec: float
    prefer_local: bool
    warm_upstream_on_miss: bool

    @classmethod
    def from_env(cls) -> "LocalDataSettings":
        return cls(
            local_read_enabled=_bool("LOCAL_BAR_READ_ENABLED", False),
            min_coverage=max(0.05, min(1.0, _float("LOCAL_BAR_MIN_COVERAGE", 0.8))),
            max_stale_sec=max(30.0, _float("LOCAL_BAR_MAX_STALE_SEC", 900.0)),
            prefer_local=_bool("LOCAL_BAR_PREFER_LOCAL", True),
            warm_upstream_on_miss=_bool("LOCAL_BAR_WARM_UPSTREAM", False),
        )

    @classmethod
    def load(cls) -> "LocalDataSettings":
        base = cls.from_env()
        overrides = _load_db_overrides()
        if not overrides:
            return base
        return cls(
            local_read_enabled=bool(overrides.get("localReadEnabled", base.local_read_enabled)),
            min_coverage=max(
                0.05,
                min(1.0, float(overrides.get("minCoverage", base.min_coverage))),
            ),
            max_stale_sec=max(
                30.0,
                float(overrides.get("maxStaleSec", base.max_stale_sec)),
            ),
            prefer_local=bool(overrides.get("preferLocal", base.prefer_local)),
            warm_upstream_on_miss=bool(
                overrides.get("warmUpstreamOnMiss", base.warm_upstream_on_miss)
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "localReadEnabled": self.local_read_enabled,
            "minCoverage": self.min_coverage,
            "maxStaleSec": self.max_stale_sec,
            "preferLocal": self.prefer_local,
            "warmUpstreamOnMiss": self.warm_upstream_on_miss,
        }


def _load_db_overrides() -> Dict[str, Any]:
    try:
        from app.services.local_data.repository import get_config_value

        raw = get_config_value("local_read")
        if isinstance(raw, dict):
            return raw
    except Exception as exc:
        logger.debug("local data config db overrides unavailable: %s", exc)
    return {}


def save_local_read_overrides(payload: Dict[str, Any]) -> Dict[str, Any]:
    from app.services.local_data.repository import set_config_value

    current = LocalDataSettings.load().to_dict()
    merged = {**current, **{k: v for k, v in payload.items() if v is not None}}
    set_config_value("local_read", merged)
    return merged

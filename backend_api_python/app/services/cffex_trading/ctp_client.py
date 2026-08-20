"""CTP channel client for mainland China futures & futures options.

Simulation mode uses in-process ``CffexRuntime`` (margin / open-close semantics).
Live mode routes through OpenCTP TdApi (``app.services.ctp_td``) and requires
``CFFEX_LIVE_TRADING_ENABLED=true`` plus broker front credentials.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.cffex_trading.runtime import CffexRuntime, CffexRuntimeError
from app.services.live_trading.base import BaseRestClient, LiveOrderResult, LiveTradingError


def _truthy(value: Optional[str]) -> bool:
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


def cffex_live_trading_enabled() -> bool:
    return _truthy(os.getenv("CFFEX_LIVE_TRADING_ENABLED"))


def _env_first(*names: str) -> str:
    for name in names:
        value = str(os.getenv(name) or "").strip()
        if value:
            return value
    return ""


@dataclass
class CtpConfig:
    broker_id: str = ""
    user_id: str = ""
    password: str = ""
    app_id: str = ""
    auth_code: str = ""
    product_info: str = ""
    td_front: str = ""
    md_front: str = ""
    investor_id: str = ""
    mode: str = "simulation"  # simulation | live
    initial_cash: float = 1_000_000.0
    account_id: str = "CTP-SIM"
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_exchange_config(cls, cfg: Dict[str, Any]) -> "CtpConfig":
        raw = dict(cfg or {})
        raw_mode = str(raw.get("mode") or raw.get("environment") or "simulation").strip().lower()
        if raw_mode in ("demo", "paper", "testnet", "simulate", "simulation"):
            mode = "simulation"
        elif raw_mode in ("live", "real", "production", "prod"):
            mode = "live"
        else:
            mode = raw_mode or "simulation"

        def pick(*keys: str, env_keys: tuple[str, ...] = ()) -> str:
            for key in keys:
                value = raw.get(key)
                if value is not None and str(value).strip():
                    return str(value).strip()
            return _env_first(*env_keys) if env_keys else ""

        user_id = pick(
            "user_id",
            "userId",
            "api_key",
            env_keys=("CTP_TD_USER_ID", "CTP_MD_USER_ID"),
        )
        return cls(
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
            td_front=pick(
                "td_front",
                "tdFront",
                "front",
                env_keys=("CTP_TD_FRONT",),
            ),
            md_front=pick(
                "md_front",
                "mdFront",
                env_keys=("CTP_MD_FRONT",),
            ),
            investor_id=pick(
                "investor_id",
                "investorId",
                env_keys=("CTP_TD_INVESTOR_ID",),
            )
            or user_id,
            mode=mode,
            initial_cash=float(raw.get("initial_cash") or raw.get("initialCash") or 1_000_000.0),
            account_id=str(raw.get("account_id") or raw.get("accountId") or "CTP-SIM").strip(),
            extra=raw,
        )


class CtpClient(BaseRestClient):
    """CTP adapter. Simulation uses ``CffexRuntime``; live uses TdApi gateway."""

    exchange_id = "ctp"

    def __init__(self, config: CtpConfig):
        super().__init__(base_url=config.td_front or "ctp://simulation")
        self.config = config
        self.runtime = CffexRuntime(
            cash=config.initial_cash,
            account_id=config.account_id or "CTP-SIM",
        )
        self._gateway = None
        if config.mode == "live":
            self._assert_live_ready()

    def _assert_live_ready(self) -> None:
        if not cffex_live_trading_enabled():
            raise LiveTradingError(
                "CTP live trading is disabled. Set CFFEX_LIVE_TRADING_ENABLED=true "
                "before routing real orders."
            )
        missing = [
            name
            for name, value in (
                ("broker_id", self.config.broker_id),
                ("user_id", self.config.user_id),
                ("password", self.config.password),
                ("td_front", self.config.td_front),
            )
            if not value
        ]
        if missing:
            raise LiveTradingError(
                f"CTP live config incomplete; missing: {', '.join(missing)}"
            )
        try:
            from app.services.ctp_td.gateway import CtpTdDependencyError, load_ctp_tdapi

            load_ctp_tdapi(str(self.config.extra.get("api_module") or "") or None)
        except CtpTdDependencyError as exc:
            raise LiveTradingError(str(exc)) from exc
        except Exception as exc:  # pragma: no cover - unexpected import failures
            raise LiveTradingError(f"CTP TdApi binding unavailable: {exc}") from exc

    def _live_gateway(self):
        if self._gateway is not None:
            return self._gateway
        from app.services.ctp_td import get_ctp_td_gateway, settings_from_mapping

        settings = settings_from_mapping(
            {
                "enabled": True,
                "td_front": self.config.td_front,
                "broker_id": self.config.broker_id,
                "user_id": self.config.user_id,
                "password": self.config.password,
                "app_id": self.config.app_id,
                "auth_code": self.config.auth_code,
                "product_info": self.config.product_info,
                "investor_id": self.config.investor_id or self.config.user_id,
                "api_module": self.config.extra.get("api_module")
                or self.config.extra.get("apiModule"),
                "flow_path": self.config.extra.get("flow_path")
                or self.config.extra.get("flowPath"),
                "order_timeout_sec": self.config.extra.get("order_timeout_sec")
                or self.config.extra.get("orderTimeoutSec"),
            }
        )
        self._gateway = get_ctp_td_gateway(settings)
        return self._gateway

    @staticmethod
    def _map_live_account(raw: Dict[str, Any]) -> Dict[str, Any]:
        available = float(raw.get("available") or 0.0)
        balance = float(raw.get("balance") or available)
        margin = float(raw.get("curr_margin") or 0.0)
        return {
            "account_id": str(raw.get("account_id") or ""),
            "currency": str(raw.get("currency") or "CNY"),
            "cash": balance,
            "used_margin": margin,
            "available": available,
            "balance": balance,
            "commission": float(raw.get("commission") or 0.0),
            "close_profit": float(raw.get("close_profit") or 0.0),
            "position_profit": float(raw.get("position_profit") or 0.0),
            "positions": [],
            "raw": raw,
        }

    @staticmethod
    def _map_live_positions(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for row in rows or []:
            direction = str(row.get("direction") or "").strip()
            # CTP PosiDirection: 2=long, 3=short
            if direction in {"2", "long", "Long"}:
                side = "long"
            elif direction in {"3", "short", "Short"}:
                side = "short"
            else:
                continue
            volume = float(row.get("position") or 0.0)
            if volume <= 0:
                continue
            instrument = str(row.get("instrument_id") or "").strip()
            cost = float(row.get("position_cost") or 0.0)
            avg = (cost / volume) if volume and cost else 0.0
            out.append(
                {
                    "symbol": instrument,
                    "side": side,
                    "volume": volume,
                    "position": volume,
                    "yesterday": float(row.get("yd_position") or 0.0),
                    "today": float(row.get("today_position") or 0.0),
                    "avg_price": avg,
                    "margin": float(row.get("use_margin") or 0.0),
                    "exchange_id": str(row.get("exchange_id") or ""),
                    "raw": row,
                }
            )
        return out

    def test_connection(self) -> Dict[str, Any]:
        if self.config.mode == "live":
            gateway = self._live_gateway()
            gateway.ensure_started()
            account = self._map_live_account(gateway.query_account())
            return {
                "ok": True,
                "exchange_id": self.exchange_id,
                "mode": self.config.mode,
                "account_id": account.get("account_id") or self.config.user_id,
                "available": account.get("available"),
                "currency": account.get("currency") or "CNY",
                "gateway": gateway.status(),
            }
        snap = self.runtime.snapshot()
        return {
            "ok": True,
            "exchange_id": self.exchange_id,
            "mode": self.config.mode,
            "account_id": snap["account_id"],
            "available": snap["available"],
            "currency": snap["currency"],
        }

    def get_account(self) -> Dict[str, Any]:
        if self.config.mode == "live":
            gateway = self._live_gateway()
            gateway.ensure_started()
            account = self._map_live_account(gateway.query_account())
            account["positions"] = self.get_positions()
            return account
        return self.runtime.snapshot()

    def get_positions(self) -> List[Dict[str, Any]]:
        if self.config.mode == "live":
            gateway = self._live_gateway()
            gateway.ensure_started()
            return self._map_live_positions(gateway.query_positions())
        return list(self.runtime.snapshot().get("positions") or [])

    def place_order(
        self,
        *,
        symbol: str,
        side: str,
        offset: str = "open",
        lots: float,
        price: float,
        order_type: str = "limit",
        wait_fill: bool = True,
        timeout_sec: Optional[float] = None,
    ) -> LiveOrderResult:
        if self.config.mode == "live":
            from app.services.ctp_td.gateway import CtpTdError

            gateway = self._live_gateway()
            try:
                fill = gateway.place_order(
                    symbol=symbol,
                    side=side,
                    offset=offset,
                    lots=lots,
                    price=price,
                    order_type=order_type,
                    wait_fill=wait_fill,
                    timeout_sec=timeout_sec,
                )
            except CtpTdError as exc:
                raise LiveTradingError(str(exc)) from exc
            return LiveOrderResult(
                exchange_id=self.exchange_id,
                exchange_order_id=str(fill.order_id),
                filled=float(fill.volume),
                avg_price=float(fill.price),
                raw={
                    "offset": offset,
                    "side": side,
                    "mode": self.config.mode,
                    "order_type": order_type,
                    "direction": fill.direction,
                    "comb_offset": fill.offset,
                    "status": fill.status,
                    **(fill.raw or {}),
                },
            )

        try:
            fill = self.runtime.place_order(
                symbol=symbol,
                side=side,
                offset=offset,
                lots=lots,
                price=price,
            )
        except CffexRuntimeError as exc:
            raise LiveTradingError(str(exc)) from exc
        return LiveOrderResult(
            exchange_id=self.exchange_id,
            exchange_order_id=fill.order_id,
            filled=float(fill.lots),
            avg_price=float(fill.price),
            raw={
                "offset": fill.offset,
                "side": fill.side,
                "margin_delta": fill.margin_delta,
                "commission": fill.commission,
                "realized_pnl": fill.realized_pnl,
                "mode": self.config.mode,
                "order_type": order_type,
                **fill.raw,
            },
        )

    def cancel_order(self, *, order_ref: str, exchange_id: str = "", instrument_id: str = "") -> None:
        if self.config.mode != "live":
            raise LiveTradingError("CTP simulation cancel is not supported")
        from app.services.ctp_td.gateway import CtpTdError

        gateway = self._live_gateway()
        try:
            gateway.cancel_order(
                order_ref=order_ref,
                exchange_id=exchange_id,
                instrument_id=instrument_id,
            )
        except CtpTdError as exc:
            raise LiveTradingError(str(exc)) from exc

"""CTP channel client for CFFEX index futures.

Live mode requires an external CTP bridge (e.g. openctp / vnpy gateway) and
``CFFEX_LIVE_TRADING_ENABLED=true``. Default mode is in-process simulation so
policy, margin, and open/close semantics can be tested without a futures seat.
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


@dataclass
class CtpConfig:
    broker_id: str = ""
    user_id: str = ""
    password: str = ""
    app_id: str = ""
    auth_code: str = ""
    td_front: str = ""
    md_front: str = ""
    investor_id: str = ""
    mode: str = "simulation"  # simulation | live
    initial_cash: float = 1_000_000.0
    account_id: str = "CTP-SIM"
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_exchange_config(cls, cfg: Dict[str, Any]) -> "CtpConfig":
        raw_mode = str(cfg.get("mode") or cfg.get("environment") or "simulation").strip().lower()
        if raw_mode in ("demo", "paper", "testnet", "simulate", "simulation"):
            mode = "simulation"
        elif raw_mode in ("live", "real", "production", "prod"):
            mode = "live"
        else:
            mode = raw_mode or "simulation"
        return cls(
            broker_id=str(cfg.get("broker_id") or cfg.get("brokerId") or "").strip(),
            user_id=str(cfg.get("user_id") or cfg.get("userId") or cfg.get("api_key") or "").strip(),
            password=str(cfg.get("password") or cfg.get("secret_key") or cfg.get("secret") or "").strip(),
            app_id=str(cfg.get("app_id") or cfg.get("appId") or "").strip(),
            auth_code=str(cfg.get("auth_code") or cfg.get("authCode") or "").strip(),
            td_front=str(cfg.get("td_front") or cfg.get("tdFront") or "").strip(),
            md_front=str(cfg.get("md_front") or cfg.get("mdFront") or "").strip(),
            investor_id=str(cfg.get("investor_id") or cfg.get("investorId") or "").strip(),
            mode=mode,
            initial_cash=float(cfg.get("initial_cash") or cfg.get("initialCash") or 1_000_000.0),
            account_id=str(cfg.get("account_id") or cfg.get("accountId") or "CTP-SIM").strip(),
            extra=dict(cfg),
        )


class CtpClient(BaseRestClient):
    """CTP adapter. Simulation uses ``CffexRuntime``; live needs a bridge."""

    exchange_id = "ctp"

    def __init__(self, config: CtpConfig):
        super().__init__(base_url=config.td_front or "ctp://simulation")
        self.config = config
        self.runtime = CffexRuntime(
            cash=config.initial_cash,
            account_id=config.account_id or "CTP-SIM",
        )
        if config.mode == "live":
            self._assert_live_ready()

    def _assert_live_ready(self) -> None:
        if not cffex_live_trading_enabled():
            raise LiveTradingError(
                "CTP live trading is disabled. Set CFFEX_LIVE_TRADING_ENABLED=true "
                "and provide a CTP bridge before routing real orders."
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
        # Native CTP bindings are operator-supplied; refuse silent pretend-live.
        raise LiveTradingError(
            "CTP live bridge is not bundled in this build. Keep mode=simulation "
            "for paper, or install/configure an external CTP gateway bridge."
        )

    def test_connection(self) -> Dict[str, Any]:
        if self.config.mode == "live":
            # Will raise until a real bridge is wired.
            self._assert_live_ready()
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
        return self.runtime.snapshot()

    def get_positions(self) -> List[Dict[str, Any]]:
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
    ) -> LiveOrderResult:
        if self.config.mode == "live":
            self._assert_live_ready()
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

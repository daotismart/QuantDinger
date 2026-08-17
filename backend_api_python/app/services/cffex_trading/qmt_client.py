"""QMT / miniQMT channel client for CFFEX index futures.

Mirrors the CTP adapter: simulation is the default; live requires
``CFFEX_LIVE_TRADING_ENABLED=true`` and an external QMT terminal bridge.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.cffex_trading.ctp_client import cffex_live_trading_enabled
from app.services.cffex_trading.runtime import CffexRuntime, CffexRuntimeError
from app.services.live_trading.base import BaseRestClient, LiveOrderResult, LiveTradingError


@dataclass
class QmtConfig:
    account_id: str = "QMT-SIM"
    qmt_path: str = ""
    session_id: str = ""
    user_id: str = ""
    password: str = ""
    mode: str = "simulation"  # simulation | live
    initial_cash: float = 1_000_000.0
    extra: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_exchange_config(cls, cfg: Dict[str, Any]) -> "QmtConfig":
        raw_mode = str(cfg.get("mode") or cfg.get("environment") or "simulation").strip().lower()
        if raw_mode in ("demo", "paper", "testnet", "simulate", "simulation"):
            mode = "simulation"
        elif raw_mode in ("live", "real", "production", "prod"):
            mode = "live"
        else:
            mode = raw_mode or "simulation"
        return cls(
            account_id=str(cfg.get("account_id") or cfg.get("accountId") or "QMT-SIM").strip(),
            qmt_path=str(cfg.get("qmt_path") or cfg.get("qmtPath") or "").strip(),
            session_id=str(cfg.get("session_id") or cfg.get("sessionId") or "").strip(),
            user_id=str(cfg.get("user_id") or cfg.get("userId") or cfg.get("api_key") or "").strip(),
            password=str(cfg.get("password") or cfg.get("secret_key") or cfg.get("secret") or "").strip(),
            mode=mode,
            initial_cash=float(cfg.get("initial_cash") or cfg.get("initialCash") or 1_000_000.0),
            extra=dict(cfg),
        )


class QmtClient(BaseRestClient):
    """miniQMT / QMT adapter with shared CFFEX margin runtime."""

    exchange_id = "qmt"

    def __init__(self, config: QmtConfig):
        super().__init__(base_url=config.qmt_path or "qmt://simulation")
        self.config = config
        self.runtime = CffexRuntime(
            cash=config.initial_cash,
            account_id=config.account_id or "QMT-SIM",
        )
        if config.mode == "live":
            self._assert_live_ready()

    def _assert_live_ready(self) -> None:
        if not cffex_live_trading_enabled():
            raise LiveTradingError(
                "QMT live trading is disabled. Set CFFEX_LIVE_TRADING_ENABLED=true "
                "and attach a miniQMT/QMT terminal before routing real orders."
            )
        if not self.config.qmt_path and not self.config.session_id:
            raise LiveTradingError(
                "QMT live config incomplete; provide qmt_path or session_id."
            )
        raise LiveTradingError(
            "QMT live bridge is not bundled in this build. Keep mode=simulation "
            "for paper, or install/configure an external miniQMT bridge."
        )

    def test_connection(self) -> Dict[str, Any]:
        if self.config.mode == "live":
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

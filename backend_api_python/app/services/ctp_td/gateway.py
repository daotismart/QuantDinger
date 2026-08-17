"""Optional OpenCTP TdApi gateway for CN futures order placement."""

from __future__ import annotations

import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.services.ctp_td.config import CtpTdSettings, settings_from_mapping
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CtpTdDependencyError(RuntimeError):
    """Raised when the optional OpenCTP trader binding is unavailable."""


class CtpTdError(RuntimeError):
    """Raised for CTP trading session / order failures."""


def load_ctp_tdapi(module_name: Optional[str] = None):
    """Import OpenCTP tdapi, or a custom module from ``CTP_TD_API_MODULE``."""
    candidates = []
    custom = (module_name or os.getenv("CTP_TD_API_MODULE") or os.getenv("CTP_MD_API_MODULE") or "").strip()
    if custom:
        candidates.append(custom)
    candidates.extend(
        [
            "openctp_ctp",
            "openctp_ctp.tdapi",
            "openctp_ctp6.6.9_P1.tdapi",
            "vnpy_ctp.api.tdapi",
        ]
    )
    errors = []
    for name in candidates:
        try:
            if name.endswith(".tdapi"):
                tdapi = __import__(name, fromlist=["*"])
                return tdapi
            module = __import__(name, fromlist=["*"])
            if hasattr(module, "tdapi"):
                return module.tdapi
            return module
        except Exception as exc:  # pragma: no cover - import probing
            errors.append(f"{name}: {exc}")
    raise CtpTdDependencyError(
        "CTP TdApi binding not installed. Install an OpenCTP Python package "
        "(e.g. `pip install openctp-ctp`) or set CTP_TD_API_MODULE. "
        f"Tried: {'; '.join(errors)}"
    )


def format_instrument_id(symbol: str, exchange: str) -> str:
    """Apply exchange InstrumentID casing conventions."""
    from app.markets.cn_futures import normalize_cn_symbol

    instrument = normalize_cn_symbol(symbol)
    ex = (exchange or "").strip().upper()
    if ex in {"CFFEX", "CZCE"}:
        return instrument.upper()
    if ex in {"SHFE", "DCE", "INE", "GFEX"}:
        # Commodity roots stay letters+digits; keep letters lower-case.
        root = "".join(ch for ch in instrument if ch.isalpha())
        month = instrument[len(root) :]
        return f"{root.lower()}{month}"
    return instrument


def resolve_exchange_id(symbol: str) -> str:
    from app.markets.cn_futures import get_future_product

    return str(get_future_product(symbol).exchange)


def map_side_offset_to_ctp(*, side: str, offset: str) -> Tuple[str, str]:
    """Return (Direction, CombOffsetFlag) for CTP InputOrderField."""
    side_l = (side or "").strip().lower()
    offset_l = (offset or "open").strip().lower()
    if side_l not in {"long", "short", "buy", "sell"}:
        raise CtpTdError(f"Unsupported CTP side: {side}")
    if offset_l in {"open"}:
        comb = "0"
    elif offset_l in {"close", "closetoday", "close_today"}:
        comb = "3" if offset_l in {"closetoday", "close_today"} else "1"
    elif offset_l in {"closeyesterday", "close_yesterday"}:
        comb = "4"
    else:
        raise CtpTdError(f"Unsupported CTP offset: {offset}")

    # long open / short close => buy; short open / long close => sell
    is_long = side_l in {"long", "buy"}
    is_open = comb == "0"
    direction = "0" if (is_long and is_open) or ((not is_long) and (not is_open)) else "1"
    # Clarified:
    # long+open -> buy(0); long+close -> sell(1)
    # short+open -> sell(1); short+close -> buy(0)
    if is_long:
        direction = "0" if is_open else "1"
    else:
        direction = "1" if is_open else "0"
    return direction, comb


def signal_to_side_offset(signal_type: str) -> Tuple[str, str]:
    sig = (signal_type or "").strip().lower()
    mapping = {
        "open_long": ("long", "open"),
        "add_long": ("long", "open"),
        "close_long": ("long", "close"),
        "reduce_long": ("long", "close"),
        "open_short": ("short", "open"),
        "add_short": ("short", "open"),
        "close_short": ("short", "close"),
        "reduce_short": ("short", "close"),
    }
    if sig not in mapping:
        raise CtpTdError(f"Unsupported signal_type for CTP: {signal_type}")
    return mapping[sig]


@dataclass
class CtpOrderFill:
    order_id: str
    instrument_id: str
    direction: str
    offset: str
    volume: float
    price: float
    status: str
    raw: Dict[str, Any] = field(default_factory=dict)


class CtpTdGateway:
    """Reconnectable CTP TraderApi session (orders / account / positions)."""

    def __init__(
        self,
        settings: Optional[CtpTdSettings] = None,
        *,
        tdapi: Any = None,
    ) -> None:
        self.settings = settings or settings_from_mapping()
        self._tdapi = tdapi
        self._api = None
        self._spi = None
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._connected = False
        self._logged_in = False
        self._settlement_confirmed = False
        self._last_error = ""
        self._request_id = 0
        self._order_ref = 0
        self._front_id = 0
        self._session_id = 0
        self._account: Dict[str, Any] = {}
        self._positions: List[Dict[str, Any]] = []
        self._order_events: Dict[str, Dict[str, Any]] = {}
        self._fill_events: Dict[str, list] = {}
        self._query_events = {
            "account": threading.Event(),
            "position": threading.Event(),
            "settlement": threading.Event(),
            "auth": threading.Event(),
            "login": threading.Event(),
        }

    @property
    def connected(self) -> bool:
        return bool(self._connected and self._logged_in and self._settlement_confirmed)

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    @property
    def last_error(self) -> str:
        return str(self._last_error or "")

    def status(self) -> dict:
        return {
            "enabled": bool(self.settings.enabled),
            "configured": bool(self.settings.configured),
            "connected": self.connected,
            "front": self.settings.front,
            "brokerId": self.settings.broker_id,
            "userId": self.settings.user_id,
            "lastError": self.last_error,
            "bindingLoaded": self._tdapi is not None or self._api is not None,
            "settlementConfirmed": bool(self._settlement_confirmed),
        }

    def start(self, *, wait_ready_sec: float = 30.0) -> None:
        if not self.settings.configured:
            raise CtpTdError("CTP TdApi settings incomplete (front/broker/user/password)")
        if self._thread and self._thread.is_alive():
            self._wait_ready(timeout=wait_ready_sec)
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_loop, name="ctp-tdapi", daemon=True)
        self._thread.start()
        self._wait_ready(timeout=wait_ready_sec)

    def stop(self) -> None:
        self._stop.set()
        api = self._api
        try:
            if api is not None and hasattr(api, "RegisterSpi"):
                api.RegisterSpi(None)
            if api is not None and hasattr(api, "Release"):
                api.Release()
        except Exception:
            logger.debug("CTP TdApi release failed", exc_info=True)
        self._api = None
        self._spi = None
        self._connected = False
        self._logged_in = False
        self._settlement_confirmed = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)

    def ensure_started(self, *, wait_ready_sec: float = 30.0) -> None:
        if self.connected:
            return
        self.start(wait_ready_sec=wait_ready_sec)

    def place_order(
        self,
        *,
        symbol: str,
        side: str,
        offset: str = "open",
        lots: float,
        price: float = 0.0,
        order_type: str = "limit",
        wait_fill: bool = True,
        timeout_sec: Optional[float] = None,
    ) -> CtpOrderFill:
        self.ensure_started()
        volume = int(round(float(lots)))
        if volume <= 0:
            raise CtpTdError("CTP order volume must be >= 1 lot")
        exchange = resolve_exchange_id(symbol)
        instrument = format_instrument_id(symbol, exchange)
        direction, comb_offset = map_side_offset_to_ctp(side=side, offset=offset)
        order_ref = self._next_order_ref()
        timeout = float(timeout_sec if timeout_sec is not None else self.settings.order_timeout_sec)

        tdapi = self._tdapi or load_ctp_tdapi(self.settings.api_module)
        req = tdapi.CThostFtdcInputOrderField()
        req.BrokerID = self.settings.broker_id
        req.InvestorID = self.settings.investor_id or self.settings.user_id
        req.UserID = self.settings.user_id
        req.ExchangeID = exchange
        req.InstrumentID = instrument
        req.OrderRef = order_ref
        req.Direction = direction
        req.CombOffsetFlag = comb_offset
        req.CombHedgeFlag = "1"  # speculation
        req.VolumeTotalOriginal = volume
        req.ContingentCondition = "1"  # immediately
        req.ForceCloseReason = "0"
        req.IsAutoSuspend = 0
        req.UserForceClose = 0
        req.MinVolume = 1
        req.VolumeCondition = "1"  # any volume
        ot = (order_type or "limit").strip().lower()
        if ot in {"market", "any"}:
            req.OrderPriceType = "1"
            req.LimitPrice = 0.0
            req.TimeCondition = "1"  # IOC
        else:
            if float(price or 0) <= 0:
                raise CtpTdError("CTP limit order requires price > 0")
            req.OrderPriceType = "2"
            req.LimitPrice = float(price)
            req.TimeCondition = "3"  # GFD

        with self._lock:
            self._order_events[order_ref] = {"status": "pending", "raw": {}}
            self._fill_events[order_ref] = []

        ret = self._api.ReqOrderInsert(req, self._next_request_id())
        if ret != 0:
            raise CtpTdError(f"ReqOrderInsert failed with code {ret}")

        if not wait_fill:
            return CtpOrderFill(
                order_id=order_ref,
                instrument_id=instrument,
                direction=direction,
                offset=comb_offset,
                volume=0.0,
                price=float(price or 0.0),
                status="submitted",
                raw={"order_ref": order_ref},
            )

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self._lock:
                fills = list(self._fill_events.get(order_ref) or [])
                meta = dict(self._order_events.get(order_ref) or {})
            status = str(meta.get("status") or "")
            if fills:
                traded = sum(float(item.get("volume") or 0) for item in fills)
                notional = sum(
                    float(item.get("volume") or 0) * float(item.get("price") or 0) for item in fills
                )
                avg = (notional / traded) if traded else float(price or 0.0)
                if traded >= volume or status in {"all_traded", "canceled", "error"}:
                    if traded <= 0 and status == "error":
                        raise CtpTdError(str(meta.get("error") or "CTP order rejected"))
                    return CtpOrderFill(
                        order_id=str(meta.get("order_sys_id") or order_ref),
                        instrument_id=instrument,
                        direction=direction,
                        offset=comb_offset,
                        volume=float(traded),
                        price=float(avg),
                        status=status or "filled",
                        raw={"order_ref": order_ref, "fills": fills, "order": meta},
                    )
            if status == "error":
                raise CtpTdError(str(meta.get("error") or "CTP order rejected"))
            time.sleep(0.05)

        raise CtpTdError(f"CTP order timed out after {timeout:.1f}s (OrderRef={order_ref})")

    def cancel_order(self, *, order_ref: str, exchange_id: str = "", instrument_id: str = "") -> None:
        self.ensure_started()
        tdapi = self._tdapi or load_ctp_tdapi(self.settings.api_module)
        req = tdapi.CThostFtdcInputOrderActionField()
        req.BrokerID = self.settings.broker_id
        req.InvestorID = self.settings.investor_id or self.settings.user_id
        req.UserID = self.settings.user_id
        req.OrderRef = str(order_ref)
        req.FrontID = int(self._front_id or 0)
        req.SessionID = int(self._session_id or 0)
        req.ActionFlag = "0"  # delete
        if exchange_id:
            req.ExchangeID = exchange_id
        if instrument_id:
            req.InstrumentID = instrument_id
        ret = self._api.ReqOrderAction(req, self._next_request_id())
        if ret != 0:
            raise CtpTdError(f"ReqOrderAction failed with code {ret}")

    def query_account(self, *, timeout_sec: float = 10.0) -> Dict[str, Any]:
        self.ensure_started()
        tdapi = self._tdapi or load_ctp_tdapi(self.settings.api_module)
        event = self._query_events["account"]
        event.clear()
        req = tdapi.CThostFtdcQryTradingAccountField()
        req.BrokerID = self.settings.broker_id
        req.InvestorID = self.settings.investor_id or self.settings.user_id
        req.CurrencyID = "CNY"
        ret = self._api.ReqQryTradingAccount(req, self._next_request_id())
        if ret != 0:
            raise CtpTdError(f"ReqQryTradingAccount failed with code {ret}")
        if not event.wait(timeout_sec):
            raise CtpTdError("CTP account query timed out")
        with self._lock:
            return dict(self._account)

    def query_positions(self, *, timeout_sec: float = 10.0) -> List[Dict[str, Any]]:
        self.ensure_started()
        tdapi = self._tdapi or load_ctp_tdapi(self.settings.api_module)
        event = self._query_events["position"]
        event.clear()
        with self._lock:
            self._positions = []
        req = tdapi.CThostFtdcQryInvestorPositionField()
        req.BrokerID = self.settings.broker_id
        req.InvestorID = self.settings.investor_id or self.settings.user_id
        ret = self._api.ReqQryInvestorPosition(req, self._next_request_id())
        if ret != 0:
            raise CtpTdError(f"ReqQryInvestorPosition failed with code {ret}")
        if not event.wait(timeout_sec):
            raise CtpTdError("CTP position query timed out")
        with self._lock:
            return list(self._positions)

    def _wait_ready(self, *, timeout: float) -> None:
        deadline = time.monotonic() + max(1.0, float(timeout))
        while time.monotonic() < deadline:
            if self.connected:
                return
            if self._last_error and not self.running:
                raise CtpTdError(self._last_error)
            time.sleep(0.05)
        raise CtpTdError(self._last_error or "CTP TdApi login/settlement timed out")

    def _run_loop(self) -> None:
        backoff = max(1.0, float(self.settings.reconnect_seconds or 5.0))
        while not self._stop.is_set():
            try:
                self._connect_once()
            except Exception as exc:
                self._last_error = str(exc)
                logger.warning("CTP TdApi session ended: %s", exc, exc_info=True)
            self._connected = False
            self._logged_in = False
            self._settlement_confirmed = False
            if self._stop.wait(backoff):
                break
            backoff = min(30.0, backoff * 1.5)

    def _connect_once(self) -> None:
        tdapi = self._tdapi or load_ctp_tdapi(self.settings.api_module)
        self._tdapi = tdapi
        flow = self.settings.flow_path
        os.makedirs(flow, exist_ok=True)
        create = getattr(tdapi, "CThostFtdcTraderApi").CreateFtdcTraderApi
        api = create(flow if flow.endswith(os.sep) else flow + os.sep)
        spi = self._build_spi(tdapi, api)
        self._api = api
        self._spi = spi
        api.RegisterSpi(spi)
        if hasattr(api, "SubscribePrivateTopic"):
            api.SubscribePrivateTopic(0)  # THOST_TERT_QUICK
        if hasattr(api, "SubscribePublicTopic"):
            api.SubscribePublicTopic(0)
        api.RegisterFront(self.settings.front)
        for key in self._query_events:
            self._query_events[key].clear()
        api.Init()

        deadline = time.monotonic() + 45.0
        while not self._stop.is_set() and time.monotonic() < deadline:
            if self.connected:
                break
            time.sleep(0.2)
        if not self.connected and not self._stop.is_set():
            raise CtpTdError(self._last_error or "CTP TdApi login timed out")

        while not self._stop.is_set() and self._connected:
            time.sleep(0.5)

    def _next_request_id(self) -> int:
        with self._lock:
            self._request_id += 1
            return self._request_id

    def _next_order_ref(self) -> str:
        with self._lock:
            self._order_ref += 1
            # Keep OrderRef short; CTP often limits length.
            return f"{self._order_ref % 1000000:06d}"

    def _rsp_failed(self, pRspInfo: Any) -> bool:
        if pRspInfo is None:
            return False
        error_id = int(getattr(pRspInfo, "ErrorID", 0) or 0)
        if error_id == 0:
            return False
        message = str(getattr(pRspInfo, "ErrorMsg", "") or "")
        self._last_error = f"CTP error {error_id}: {message}"
        logger.warning(self._last_error)
        return True

    def _authenticate_or_login(self, tdapi: Any, api: Any) -> None:
        if (
            self.settings.app_id
            and self.settings.auth_code
            and hasattr(tdapi, "CThostFtdcReqAuthenticateField")
            and hasattr(api, "ReqAuthenticate")
        ):
            req = tdapi.CThostFtdcReqAuthenticateField()
            req.BrokerID = self.settings.broker_id
            req.UserID = self.settings.user_id
            req.AppID = self.settings.app_id
            req.AuthCode = self.settings.auth_code
            if self.settings.product_info and hasattr(req, "UserProductInfo"):
                req.UserProductInfo = self.settings.product_info
            self._query_events["auth"].clear()
            api.ReqAuthenticate(req, self._next_request_id())
            return
        self._login(tdapi, api)

    def _login(self, tdapi: Any, api: Any) -> None:
        req = tdapi.CThostFtdcReqUserLoginField()
        req.BrokerID = self.settings.broker_id
        req.UserID = self.settings.user_id
        req.Password = self.settings.password
        if self.settings.product_info and hasattr(req, "UserProductInfo"):
            req.UserProductInfo = self.settings.product_info
        self._query_events["login"].clear()
        api.ReqUserLogin(req, self._next_request_id())

    def _confirm_settlement(self, tdapi: Any, api: Any) -> None:
        req = tdapi.CThostFtdcSettlementInfoConfirmField()
        req.BrokerID = self.settings.broker_id
        req.InvestorID = self.settings.investor_id or self.settings.user_id
        self._query_events["settlement"].clear()
        api.ReqSettlementInfoConfirm(req, self._next_request_id())

    def _build_spi(self, tdapi: Any, api: Any):
        gateway = self
        base = tdapi.CThostFtdcTraderSpi

        class _Spi(base):  # type: ignore[misc,valid-type]
            def OnFrontConnected(self):
                gateway._connected = True
                gateway._last_error = ""
                logger.info("CTP TdApi front connected: %s", gateway.settings.front)
                gateway._authenticate_or_login(tdapi, api)

            def OnFrontDisconnected(self, nReason):
                gateway._connected = False
                gateway._logged_in = False
                gateway._settlement_confirmed = False
                gateway._last_error = f"front disconnected reason={nReason}"
                logger.warning("CTP TdApi %s", gateway._last_error)

            def OnRspAuthenticate(self, pRspAuthenticateField, pRspInfo, nRequestID, bIsLast):
                if gateway._rsp_failed(pRspInfo):
                    gateway._query_events["auth"].set()
                    return
                gateway._login(tdapi, api)

            def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast):
                if gateway._rsp_failed(pRspInfo):
                    gateway._logged_in = False
                    gateway._query_events["login"].set()
                    return
                gateway._logged_in = True
                gateway._last_error = ""
                if pRspUserLogin is not None:
                    gateway._front_id = int(getattr(pRspUserLogin, "FrontID", 0) or 0)
                    gateway._session_id = int(getattr(pRspUserLogin, "SessionID", 0) or 0)
                logger.info(
                    "CTP TdApi login ok broker=%s user=%s",
                    gateway.settings.broker_id,
                    gateway.settings.user_id,
                )
                gateway._confirm_settlement(tdapi, api)
                gateway._query_events["login"].set()

            def OnRspSettlementInfoConfirm(self, pSettlementInfoConfirm, pRspInfo, nRequestID, bIsLast):
                if gateway._rsp_failed(pRspInfo):
                    gateway._query_events["settlement"].set()
                    return
                gateway._settlement_confirmed = True
                gateway._last_error = ""
                logger.info("CTP TdApi settlement confirmed")
                gateway._query_events["settlement"].set()

            def OnRspOrderInsert(self, pInputOrder, pRspInfo, nRequestID, bIsLast):
                order_ref = str(getattr(pInputOrder, "OrderRef", "") or "") if pInputOrder else ""
                if gateway._rsp_failed(pRspInfo):
                    with gateway._lock:
                        gateway._order_events[order_ref] = {
                            "status": "error",
                            "error": gateway._last_error,
                            "raw": {},
                        }

            def OnErrRtnOrderInsert(self, pInputOrder, pRspInfo):
                order_ref = str(getattr(pInputOrder, "OrderRef", "") or "") if pInputOrder else ""
                gateway._rsp_failed(pRspInfo)
                with gateway._lock:
                    gateway._order_events[order_ref] = {
                        "status": "error",
                        "error": gateway._last_error,
                        "raw": {},
                    }

            def OnRtnOrder(self, pOrder):
                if pOrder is None:
                    return
                order_ref = str(getattr(pOrder, "OrderRef", "") or "")
                status_code = str(getattr(pOrder, "OrderStatus", "") or "")
                status_map = {
                    "0": "all_traded",
                    "1": "partial",
                    "3": "not_traded",
                    "5": "canceled",
                    "a": "unknown",
                }
                with gateway._lock:
                    gateway._order_events[order_ref] = {
                        "status": status_map.get(status_code, status_code or "working"),
                        "order_sys_id": str(getattr(pOrder, "OrderSysID", "") or "").strip(),
                        "status_msg": str(getattr(pOrder, "StatusMsg", "") or ""),
                        "raw": {
                            "OrderStatus": status_code,
                            "VolumeTraded": getattr(pOrder, "VolumeTraded", 0),
                            "VolumeTotal": getattr(pOrder, "VolumeTotal", 0),
                        },
                    }

            def OnRtnTrade(self, pTrade):
                if pTrade is None:
                    return
                order_ref = str(getattr(pTrade, "OrderRef", "") or "")
                fill = {
                    "volume": float(getattr(pTrade, "Volume", 0) or 0),
                    "price": float(getattr(pTrade, "Price", 0) or 0),
                    "trade_id": str(getattr(pTrade, "TradeID", "") or "").strip(),
                    "order_sys_id": str(getattr(pTrade, "OrderSysID", "") or "").strip(),
                }
                with gateway._lock:
                    gateway._fill_events.setdefault(order_ref, []).append(fill)

            def OnRspQryTradingAccount(self, pTradingAccount, pRspInfo, nRequestID, bIsLast):
                if gateway._rsp_failed(pRspInfo):
                    gateway._query_events["account"].set()
                    return
                if pTradingAccount is not None:
                    with gateway._lock:
                        gateway._account = {
                            "account_id": str(getattr(pTradingAccount, "AccountID", "") or ""),
                            "broker_id": str(getattr(pTradingAccount, "BrokerID", "") or ""),
                            "currency": str(getattr(pTradingAccount, "CurrencyID", "") or "CNY"),
                            "balance": float(getattr(pTradingAccount, "Balance", 0) or 0),
                            "available": float(getattr(pTradingAccount, "Available", 0) or 0),
                            "curr_margin": float(getattr(pTradingAccount, "CurrMargin", 0) or 0),
                            "frozen_margin": float(getattr(pTradingAccount, "FrozenMargin", 0) or 0),
                            "commission": float(getattr(pTradingAccount, "Commission", 0) or 0),
                            "close_profit": float(getattr(pTradingAccount, "CloseProfit", 0) or 0),
                            "position_profit": float(getattr(pTradingAccount, "PositionProfit", 0) or 0),
                        }
                if bIsLast:
                    gateway._query_events["account"].set()

            def OnRspQryInvestorPosition(self, pInvestorPosition, pRspInfo, nRequestID, bIsLast):
                if gateway._rsp_failed(pRspInfo):
                    gateway._query_events["position"].set()
                    return
                if pInvestorPosition is not None:
                    pos = {
                        "instrument_id": str(getattr(pInvestorPosition, "InstrumentID", "") or ""),
                        "exchange_id": str(getattr(pInvestorPosition, "ExchangeID", "") or ""),
                        "direction": str(getattr(pInvestorPosition, "PosiDirection", "") or ""),
                        "hedge_flag": str(getattr(pInvestorPosition, "HedgeFlag", "") or ""),
                        "position": float(getattr(pInvestorPosition, "Position", 0) or 0),
                        "today_position": float(getattr(pInvestorPosition, "TodayPosition", 0) or 0),
                        "yd_position": float(getattr(pInvestorPosition, "YdPosition", 0) or 0),
                        "use_margin": float(getattr(pInvestorPosition, "UseMargin", 0) or 0),
                        "position_cost": float(getattr(pInvestorPosition, "PositionCost", 0) or 0),
                    }
                    if float(pos["position"] or 0) != 0:
                        with gateway._lock:
                            gateway._positions.append(pos)
                if bIsLast:
                    gateway._query_events["position"].set()

        return _Spi()


_gateway_lock = threading.RLock()
_gateways: Dict[str, CtpTdGateway] = {}


def _gateway_key(settings: CtpTdSettings) -> str:
    return "|".join(
        [
            settings.front,
            settings.broker_id,
            settings.user_id,
            settings.investor_id or settings.user_id,
        ]
    )


def get_ctp_td_gateway(settings: Optional[CtpTdSettings] = None) -> CtpTdGateway:
    cfg = settings or settings_from_mapping()
    key = _gateway_key(cfg)
    with _gateway_lock:
        gateway = _gateways.get(key)
        if gateway is None:
            gateway = CtpTdGateway(cfg)
            _gateways[key] = gateway
        return gateway

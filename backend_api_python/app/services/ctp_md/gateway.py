"""Optional OpenCTP MdApi gateway for CN futures ticks."""

from __future__ import annotations

import os
import threading
import time
from typing import Any, Callable, Iterable, Optional, Set

from app.services.ctp_md.config import CtpMdConfig, CtpMdSettings
from app.services.ctp_md.models import CtpTick, tick_from_depth_market_data
from app.services.ctp_md.store import CtpTickStore, get_ctp_tick_store
from app.services.ctp_md.symbols import normalize_ctp_instrument, unique_instruments
from app.markets.cn_futures_sessions import (
    filter_collectible_instruments,
    md_connection_open,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CtpMdDependencyError(RuntimeError):
    """Raised when the optional OpenCTP binding is unavailable."""


def load_ctp_mdapi(module_name: Optional[str] = None):
    """Import OpenCTP mdapi, or a custom module from ``CTP_MD_API_MODULE``."""
    candidates = []
    custom = (module_name or os.getenv("CTP_MD_API_MODULE") or "").strip()
    if custom:
        candidates.append(custom)
    candidates.extend(
        [
            "openctp_ctp",
            "openctp_ctp.mdapi",
            "openctp_ctp6.6.9_P1.mdapi",
            "vnpy_ctp.api.mdapi",
        ]
    )
    errors = []
    for name in candidates:
        try:
            if name.endswith(".mdapi"):
                package = name.rsplit(".", 1)[0]
                mdapi = __import__(name, fromlist=["*"])
                return mdapi
            module = __import__(name, fromlist=["*"])
            if hasattr(module, "mdapi"):
                return module.mdapi
            return module
        except Exception as exc:  # pragma: no cover - import probing
            errors.append(f"{name}: {exc}")
    raise CtpMdDependencyError(
        "CTP MdApi binding not installed. Install an OpenCTP Python package "
        "(e.g. `pip install openctp-ctp`) or set CTP_MD_API_MODULE. "
        f"Tried: {'; '.join(errors)}"
    )


class CtpMdGateway:
    """Reconnectable CTP market-data session (MdApi only, no trading)."""

    def __init__(
        self,
        settings: Optional[CtpMdSettings] = None,
        *,
        store: Optional[CtpTickStore] = None,
        mdapi: Any = None,
        on_tick: Optional[Callable[[CtpTick], None]] = None,
    ) -> None:
        self.settings = settings or CtpMdConfig.settings()
        self.store = store or get_ctp_tick_store()
        self._mdapi = mdapi
        self._on_tick = on_tick
        self._api = None
        self._spi = None
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._connected = False
        self._logged_in = False
        self._last_error = ""
        self._subscribed: Set[str] = set()
        self._pending_subscribe: Set[str] = set(unique_instruments(self.settings.instruments))
        self._request_id = 0

    @property
    def connected(self) -> bool:
        return bool(self._connected and self._logged_in)

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    @property
    def last_error(self) -> str:
        return str(self._last_error or "")

    def status(self) -> dict:
        with self._lock:
            return {
                "enabled": bool(self.settings.enabled),
                "configured": bool(self.settings.configured),
                "connected": self.connected,
                "front": self.settings.front,
                "brokerId": self.settings.broker_id,
                "userId": self.settings.user_id,
                "subscribed": sorted(self._subscribed),
                "pendingSubscribe": sorted(self._pending_subscribe),
                "lastError": self.last_error,
                "bindingLoaded": self._mdapi is not None or self._api is not None,
                "sessionOpen": self._session_should_connect(),
                "sessionCollectible": self._collectible_instruments(),
            }

    def start(self) -> None:
        if not self.settings.enabled:
            logger.info("CTP MdApi gateway disabled (CTP_MD_ENABLED!=true)")
            return
        if not self.settings.configured:
            self._last_error = "CTP MdApi is enabled but front/broker/user is incomplete"
            logger.warning(self._last_error)
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name=f"CtpMdGateway-{id(self)}",
            daemon=True,
        )
        self._thread.start()

    def _watched_instruments(self) -> list[str]:
        with self._lock:
            items = unique_instruments(
                list(self._pending_subscribe)
                + list(self._subscribed)
                + list(self.settings.instruments or [])
            )
        return items

    def _collectible_instruments(self) -> list[str]:
        return filter_collectible_instruments(self._watched_instruments())

    def _session_should_connect(self) -> bool:
        return md_connection_open(self._watched_instruments())

    def _wait_for_session(self) -> None:
        logged = False
        while not self._stop.is_set() and not self._session_should_connect():
            if not logged:
                logger.info(
                    "CTP MdApi waiting for next CN futures session (watch=%s)",
                    ",".join(self._watched_instruments()) or "(none)",
                )
                logged = True
            if self._stop.wait(15.0):
                return
        if logged and not self._stop.is_set():
            logger.info("CTP MdApi session window open, connecting")

    def _release_api(self) -> None:
        api = self._api
        self._api = None
        self._spi = None
        self._connected = False
        self._logged_in = False
        if api is None:
            return
        try:
            api.RegisterSpi(None)
        except Exception:
            pass
        try:
            release = getattr(api, "Release", None)
            if callable(release):
                release()
        except Exception:
            pass

    def stop(self, timeout: float = 3.0) -> None:
        self._stop.set()
        self._release_api()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=max(0.0, float(timeout or 0.0)))
        self._connected = False
        self._logged_in = False

    def subscribe(self, instruments: Iterable[str]) -> list[str]:
        ids = unique_instruments(instruments)
        with self._lock:
            for instrument in ids:
                self._pending_subscribe.add(instrument)
            logged_in = self._logged_in
            api = self._api
        collectible = filter_collectible_instruments(ids)
        if logged_in and api is not None and collectible:
            self._do_subscribe(api, collectible)
        return ids

    def unsubscribe(self, instruments: Iterable[str]) -> list[str]:
        ids = unique_instruments(instruments)
        with self._lock:
            for instrument in ids:
                self._pending_subscribe.discard(instrument)
                self._subscribed.discard(instrument)
            api = self._api
            logged_in = self._logged_in
        if logged_in and api is not None and ids:
            try:
                api.UnSubscribeMarketData([item.encode("utf-8") for item in ids], len(ids))
            except Exception as exc:
                logger.debug("CTP unsubscribe failed: %s", exc)
        return ids

    def inject_tick(self, tick: CtpTick) -> None:
        """Test/helper hook to push a normalized tick without a live front."""
        self.store.put(tick)
        if self._on_tick is not None:
            self._on_tick(tick)

    def _run(self) -> None:
        backoff = max(1.0, float(self.settings.reconnect_seconds or 5.0))
        while not self._stop.is_set():
            self._wait_for_session()
            if self._stop.is_set():
                break
            try:
                self._connect_once()
            except CtpMdDependencyError as exc:
                self._last_error = str(exc)
                logger.error(self._last_error)
                break
            except Exception as exc:
                self._last_error = str(exc)
                logger.warning("CTP MdApi session error: %s", exc)
            self._release_api()
            if self._stop.is_set():
                break
            if not self._session_should_connect():
                backoff = max(1.0, float(self.settings.reconnect_seconds or 5.0))
                continue
            if self._stop.wait(backoff):
                break
            backoff = min(30.0, backoff * 1.5)

    def _connect_once(self) -> None:
        mdapi = self._mdapi or load_ctp_mdapi()
        self._mdapi = mdapi
        flow = self.settings.flow_path
        os.makedirs(flow, exist_ok=True)
        create = getattr(mdapi, "CThostFtdcMdApi").CreateFtdcMdApi
        api = create(flow if flow.endswith(os.sep) else flow + os.sep)
        spi = self._build_spi(mdapi, api)
        self._api = api
        self._spi = spi
        api.RegisterSpi(spi)
        api.RegisterFront(self.settings.front)
        api.Init()
        # Keep the worker thread alive while CTP callbacks run in native threads.
        deadline = time.monotonic() + 30.0
        while not self._stop.is_set() and time.monotonic() < deadline:
            if self._logged_in:
                break
            time.sleep(0.2)
        if not self._logged_in and not self._stop.is_set():
            raise RuntimeError(self._last_error or "CTP MdApi login timed out")
        # Park until disconnect, stop, or the CN futures session window closes.
        while not self._stop.is_set() and self._connected:
            if not self._session_should_connect():
                logger.info("CTP MdApi session window closed, releasing front")
                break
            time.sleep(1.0)

    def _next_request_id(self) -> int:
        with self._lock:
            self._request_id += 1
            return self._request_id

    def _build_spi(self, mdapi: Any, api: Any):
        gateway = self
        base = mdapi.CThostFtdcMdSpi

        class _Spi(base):  # type: ignore[misc,valid-type]
            def OnFrontConnected(self):
                gateway._connected = True
                gateway._last_error = ""
                logger.info("CTP MdApi front connected: %s", gateway.settings.front)
                try:
                    if (
                        gateway.settings.app_id
                        and gateway.settings.auth_code
                        and hasattr(mdapi, "CThostFtdcReqAuthenticateField")
                        and hasattr(api, "ReqAuthenticate")
                    ):
                        req = mdapi.CThostFtdcReqAuthenticateField()
                        req.BrokerID = gateway.settings.broker_id
                        req.UserID = gateway.settings.user_id
                        req.AppID = gateway.settings.app_id
                        req.AuthCode = gateway.settings.auth_code
                        if gateway.settings.product_info and hasattr(req, "UserProductInfo"):
                            req.UserProductInfo = gateway.settings.product_info
                        api.ReqAuthenticate(req, gateway._next_request_id())
                        return
                except AttributeError:
                    logger.warning(
                        "CTP MdApi ReqAuthenticate unsupported; falling back to UserLogin"
                    )
                gateway._login(mdapi, api)

            def OnFrontDisconnected(self, nReason):
                gateway._connected = False
                gateway._logged_in = False
                gateway._last_error = f"front disconnected reason={nReason}"
                logger.warning("CTP MdApi %s", gateway._last_error)

            def OnRspAuthenticate(self, pRspAuthenticateField, pRspInfo, nRequestID, bIsLast):
                if gateway._rsp_failed(pRspInfo):
                    return
                gateway._login(mdapi, api)

            def OnRspUserLogin(self, pRspUserLogin, pRspInfo, nRequestID, bIsLast):
                if gateway._rsp_failed(pRspInfo):
                    gateway._logged_in = False
                    return
                gateway._logged_in = True
                gateway._last_error = ""
                logger.info("CTP MdApi login ok broker=%s user=%s", gateway.settings.broker_id, gateway.settings.user_id)
                with gateway._lock:
                    pending = sorted(gateway._pending_subscribe | gateway._subscribed)
                collectible = filter_collectible_instruments(pending)
                if collectible:
                    gateway._do_subscribe(api, collectible)

            def OnRspSubMarketData(self, pSpecificInstrument, pRspInfo, nRequestID, bIsLast):
                if gateway._rsp_failed(pRspInfo):
                    return
                instrument = ""
                if pSpecificInstrument is not None:
                    instrument = str(getattr(pSpecificInstrument, "InstrumentID", "") or "")
                instrument = normalize_ctp_instrument(instrument)
                if instrument:
                    with gateway._lock:
                        gateway._subscribed.add(instrument)
                        gateway._pending_subscribe.discard(instrument)

            def OnRtnDepthMarketData(self, pDepthMarketData):
                tick = tick_from_depth_market_data(
                    pDepthMarketData,
                    received_at_ms=int(time.time() * 1000),
                )
                if tick is None:
                    return
                gateway.inject_tick(tick)

        return _Spi()

    def _login(self, mdapi: Any, api: Any) -> None:
        req = mdapi.CThostFtdcReqUserLoginField()
        req.BrokerID = self.settings.broker_id
        req.UserID = self.settings.user_id
        req.Password = self.settings.password
        if self.settings.product_info and hasattr(req, "UserProductInfo"):
            req.UserProductInfo = self.settings.product_info
        api.ReqUserLogin(req, self._next_request_id())

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

    def _do_subscribe(self, api: Any, instruments: list[str]) -> None:
        ids = unique_instruments(instruments)
        if not ids:
            return
        try:
            payload = [item.encode("utf-8") for item in ids]
            api.SubscribeMarketData(payload, len(payload))
            logger.info("CTP MdApi subscribe requested: %s", ",".join(ids))
        except Exception as exc:
            self._last_error = f"subscribe failed: {exc}"
            logger.warning("CTP MdApi %s", self._last_error)


_GATEWAY: Optional[CtpMdGateway] = None
_GATEWAY_LOCK = threading.Lock()


def get_ctp_md_gateway() -> CtpMdGateway:
    global _GATEWAY
    if _GATEWAY is None:
        with _GATEWAY_LOCK:
            if _GATEWAY is None:
                _GATEWAY = CtpMdGateway()
    return _GATEWAY

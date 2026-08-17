# CTP MdApi 逐笔行情接入

QuantDinger 可通过上期技术 **CTP MdApi** 接入国内期货 **tick/深度行情推送**。
本能力仅覆盖**行情**，不包含 CTP 交易下单（TdApi）。

## 接入内容

网关订阅后接收 `OnRtnDepthMarketData`，规范化为 tick（最新价、买一卖一、成交量、持仓量、时间戳等），并提供：

- 进程内 tick 缓存，供 `FuturesDataSource.get_ticker` 优先读取
- 当 `exchange_id=ctp` 时，实盘价格流使用 `CtpTickPriceFeed`
- HTTP：`/api/ctp-md/*`

策略主信号仍按**已完成 K 线**驱动；tick 用于实时价格、风控与价格 tick 类机器人路径。

## 依赖

1. 可连通的 CTP **行情前置**（SimNow 或期货公司 Md 前置）
2. OpenCTP 兼容 Python 绑定，例如：

```bash
pip install openctp-ctp
```

也可通过 `CTP_MD_API_MODULE` 指定自定义 mdapi 模块。

## 配置

在 `backend_api_python/.env` 中配置（详见 `env.example`）：

- `CTP_MD_ENABLED=true`
- `CTP_MD_FRONT=tcp://host:port`
- `CTP_MD_BROKER_ID` / `CTP_MD_USER_ID` / `CTP_MD_PASSWORD`
- 可选：`CTP_MD_APP_ID` / `CTP_MD_AUTH_CODE`
- `CTP_MD_INSTRUMENTS=rb2505,ag2506,IF2503`

Tick 采集按品种**主交易时段**（北京时间）开关：中金所日盘、商品日盘（含午休/茶歇保持连接）、夜盘（21:00–23:00 / 01:00 / 02:30），含周五夜盘跨周六凌晨与周日夜盘。休市时释放 MdApi 前置，避免反复重连。可用 `CTP_MD_IGNORE_SESSION=true` 关闭此时段门控。

## 接口

- `GET /api/ctp-md/status`
- `GET /api/ctp-md/ticks`
- `GET /api/ctp-md/tick?symbol=rb2505`
- `POST /api/ctp-md/subscribe`

## 说明

- 不包含 CTP 下单
- 未安装 native 绑定时，期货 ticker 仍走原有 Twelve Data / yfinance / CCXT 降级链

## 数据维护

建议同时启用 `MARKET_DATA_MAINT_ENABLED=true`，由实时/历史维护程序保证 tick 与 1m K 线连续准确，见 `docs/trading/MARKET_DATA_MAINT_GUIDE_CN.md`。

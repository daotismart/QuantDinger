# Production host sync (daotismart)

Operator notes for the QuantDinger instance previously deployed by a cloud agent.
**Do not put passwords, API keys, or CTP secrets in this file.** Live secrets stay on the host.

## Host

| Item | Value |
| --- | --- |
| Public IP | `129.211.55.75` |
| OS | TencentOS / kernel 6.6 (`VM-0-3-tencentos`) |
| Deploy root | `/database/ai/` |
| QuantDinger dir | `/database/ai/QuantDinger` |
| Web UI | `http://129.211.55.75:8820/` |
| API (loopback on host) | `http://127.0.0.1:5000` |
| Credentials file on host | `/database/ai/QuantDinger/.deploy-credentials.txt` |

SSH as `root@129.211.55.75`. Prefer key-based auth. Rotate any password that was shared in chat.

## Compose

Active project name: `quantdinger`

```bash
cd /database/ai/QuantDinger
# Canonical command (also in .deploy-compose):
docker compose \
  -f docker-compose.yml \
  -f docker-compose.production.yml \
  -f docker-compose.hotfix.yml \
  ps
```

Images in use (as of last sync):

- Backend / workers: `quantdinger-backend:ctp`
- Frontend: `quantdinger-frontend:datasvc` (`pull_policy: never`)
- Postgres / Redis: DaoCloud mirrors of official images

Published ports:

- Frontend nginx: `0.0.0.0:8820 -> 80`
- Backend: `127.0.0.1:5000 -> 5000`
- Postgres: `127.0.0.1:5432 -> 5432`
- Redis cache: `127.0.0.1:6379 -> 6379`

## Git on host

| Repo path | Notes |
| --- | --- |
| `/database/ai/QuantDinger` | remotes `origin` + `mirror` (ghfast.top); often on a `cursor/*` deploy branch with local hotfix edits |
| `/database/ai/QuantDinger/QuantDinger-Vue` | built into `quantdinger-frontend:datasvc`; `.DEPLOY_SOURCE` records Vue branch used for the image |

Expect uncommitted hotfix files under `docker-compose.hotfix.yml`, `ops/hotfixes/`, and occasional backend route/service patches. Treat the host tree as **deployment state**, not a clean CI checkout.

## Runtime features observed

- Process roles: `backend`, `trading-worker`, `scheduler-worker`, `celery-worker`, `celery-beat`, `frontend`, `postgres`, `redis`, `redis-jobs`
- Markets include CN futures / options; CTP MD/TD enabled in `backend_api_python/.env`
- Custom LLM gateway: `CUSTOM_API_URL` points at host LLM gateway (`:8080/v1`, TradingAgents stack)
- Admin bootstrap user name is stored in host `.env` / `.deploy-credentials.txt` (not duplicated here)

## Health checks

On the host:

```bash
curl -sS http://127.0.0.1:5000/api/health
curl -sS http://127.0.0.1:5000/api/health/ready
curl -sS http://127.0.0.1:8820/api/health
docker ps --filter name=quantdinger-celery-worker
```

From outside:

```bash
curl -sS http://129.211.55.75:8820/api/health
```

### Celery worker notes

This host keeps `CELERY_CONCURRENCY=1` because RAM is tight (~3.6 GiB shared with other stacks). Long `market_data_historical_maint` jobs therefore monopolize the only worker slot. Mitigations in use:

- historical cycles emit worker heartbeats between symbols;
- `CELERY_HEALTH_MAX_AGE_SEC=1800` on the celery health check;
- `MARKET_DATA_MAINT_HISTORICAL_INTERVAL_SEC=900` to reduce overlap.

Do not raise concurrency without checking free memory first.

## Other stacks on the same machine

Same `/database/ai/` host also runs:

- `etf_options` (ClickHouse / Dash / gateway on various ports)
- `tradingagents` (nginx `:8880`, LLM gateway `:8080`)

Do not reclaim those ports when redeploying QuantDinger.

## Agent workflow

1. SSH to host (key preferred).
2. Inspect `DEPLOY_STATUS.txt`, `.deploy-compose`, `docker compose ps`.
3. Change code on a feature branch locally; ship via image rebuild or controlled hotfix under `ops/hotfixes/` + `docker-compose.hotfix.yml`.
4. Never commit host `.env`, `.deploy-credentials.txt`, or CTP credentials into git.
5. After deploy, re-check `/api/health` and `/api/health/ready`, and note `celery-worker` health if it was previously unhealthy.

## Frontend hotfix warning

Do **not** bind-mount individual hashed Vite chunks from `ops/hotfixes/*.js` onto
`quantdinger-frontend` unless the entire dependent chunk graph is mounted too.

A previous mount of `QuickTradePanel-B0Dq_CAe.js` reused the current filename but
imported missing older chunks (`market-CGhPjXGb`, `broker-DL9eAdB-`, `index-CNkhJNEQ`),
which hung the SPA (including Indicator) with dynamic-import 404s.

Current mitigation on the host:

- no stale JS chunk mounts;
- nginx `/assets/` served with `Cache-Control: no-cache` temporarily;
- QuickTradePanel chunk renamed to `QuickTradePanel-B0Dq_CAeR2.js` inside the image
  so browsers drop the poisoned cache entry.

Indicator page route: `#/indicator-ide` (legacy `#/indicator-analysis` redirects there).

### Strategy Management menu (recurring)

The production `fe-compat` sidebar often collapses **Strategy** to IDE-only
after an assets refresh. Restore with:

```bash
python3 /database/ai/QuantDinger/ops/hotfixes/strategy-manage-restore/restore_strategy_manage_menu.py
# compose must mount strategy-manage.html (script adds it if missing)
cd /database/ai/QuantDinger && docker compose \
  -f docker-compose.yml -f docker-compose.production.yml \
  -f docker-compose.hotfix.yml up -d --no-deps frontend
```

Required frontend volume (do **not** mount individual hashed JS chunks):

```yaml
- ./ops/hotfixes/fe-compat/strategy-manage.html:/usr/share/nginx/html/strategy-manage.html:ro
```

Re-run the restore script after any `ops/hotfixes/fe-compat/assets` replacement.
The inventory API is `GET /api/strategies/inventory` (backend hotfix).

Crypto OHLCV from this host currently times out without `PROXY_URL` (Binance/OKX
unreachable). USStock / CNFutures kline still work.

## CN futures history backfill

Catalog targets: continuous roots (`RB0`, `IF0`, …) across CFFEX / SHFE / DCE /
CZCE / INE / GFEX (`CNFutures` + `CNIndexFutures`), ~77 symbols.

Script (inside `quantdinger-backend`):

```bash
python scripts/ingest_cn_futures_history.py --persist \
  --timeframes 1D,1W \
  -o /tmp/cn_futures_ingest_daily.json

# Intraday: stitch nearby months; --no-resume refreshes symbols that already
# have many 1m bars but a stale max(bar_time).
python scripts/ingest_cn_futures_history.py --persist \
  --timeframes 1m,5m,15m,30m,1H \
  --stitch-months 12 --no-resume --watch-intraday \
  -o /tmp/cn_futures_ingest_minute.json
```

Host-side run pattern (do **not** recreate `quantdinger-backend` while this
`docker exec` is live):

```bash
cd /database/ai/QuantDinger
nohup docker exec -e QD_PROCESS_ROLE=celery \
  -e CN_FUTURES_INGEST_PERSIST=1 \
  -e CN_FUTURES_MARKET_DATA_PROVIDER=akshare \
  -e CN_FUTURES_MINUTE_STITCH_MONTHS=12 \
  quantdinger-backend \
  python scripts/ingest_cn_futures_history.py --persist \
    --timeframes 1m,5m,15m,30m,1H \
    --stitch-months 12 --no-resume --watch-intraday \
    -o /tmp/cn_futures_ingest_minute.json \
  > ops/cn_futures_ingest_minute_$(date +%Y%m%d_%H%M%S).log 2>&1 &
```

Status as of 2026-08-20:

- Daily/weekly phase completed (`ok=77`, large upsert into `qd_market_bars`).
- Minute phase re-started with `--no-resume` after an earlier run was killed by
  a backend recreate; logs under `ops/cn_futures_ingest_minute_*.log`.
- Derived TFs (`5m`/`15m`/`30m`/`1H`) come from stitched `1m` when requested
  together.

Coverage check:

```bash
docker exec quantdinger-db psql -U quantdinger -d quantdinger -c \
  "SELECT market, timeframe, COUNT(DISTINCT symbol), MAX(bar_time)
   FROM qd_market_bars
   WHERE market IN ('CNFutures','CNIndexFutures')
   GROUP BY 1,2 ORDER BY 1,2;"
```

## CN ETF options history ingest

Listed SSE/SZSE ETF option contracts plus the underlying ETF (and benchmark index) daily/weekly bars.

**Primary production path is host crontab**, not Celery Beat. The host keeps `CELERY_CONCURRENCY=1`; a full options ingest would starve other maintenance if it ran on the worker.

Script inside `quantdinger-backend`:

```bash
python scripts/ingest_cn_etf_options_history.py --persist \
  --timeframes 1D,1W \
  -o /tmp/cn_etf_options_ingest.json
```

Host cron (Asia/Shanghai, weekdays 16:40). Copy `scripts/ops/cron-cn-etf-options-ingest.sh` onto the host and install:

```bash
chmod +x /database/ai/QuantDinger/scripts/ops/cron-cn-etf-options-ingest.sh
crontab -l | grep -v cron-cn-etf-options-ingest.sh | crontab -
(crontab -l 2>/dev/null; echo '40 16 * * 1-5 TZ=Asia/Shanghai /database/ai/QuantDinger/scripts/ops/cron-cn-etf-options-ingest.sh') | crontab -
```

Logs: `/database/ai/QuantDinger/ops/cn_etf_options_ingest_*.log`. Overlapping runs are skipped via `flock`.

Do **not** recreate `quantdinger-backend` while an ingest `docker exec` is live.

Optional Celery Beat backup (disabled by default): set `CN_ETF_OPTIONS_INGEST_ENABLED=true` on the worker. Keep host cron as the source of truth to avoid double-load.

Coverage check:

```bash
docker exec quantdinger-db psql -U quantdinger -d quantdinger -c \
  "SELECT market, timeframe, COUNT(DISTINCT symbol), MAX(bar_time)
   FROM qd_market_bars
   WHERE market IN ('CNIndexOptions','CNStock')
     AND (symbol ~ '^[0-9]{8}$' OR symbol IN ('510050.SH','510300.SH','510500.SH'))
   GROUP BY 1,2 ORDER BY 1,2;"
```

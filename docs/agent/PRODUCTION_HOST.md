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
```

From outside:

```bash
curl -sS http://129.211.55.75:8820/api/health
```

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

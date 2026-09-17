#!/usr/bin/env bash
# Post-close CN ETF options + underlying daily/weekly ingest.
# Intended for the production host crontab (Asia/Shanghai 16:40 Mon-Fri).
# Does NOT recreate containers. Safe to overlap-guard with flock.
set -euo pipefail

ROOT="${QUANTDINGER_ROOT:-/database/ai/QuantDinger}"
CONTAINER="${QUANTDINGER_BACKEND_CONTAINER:-quantdinger-backend}"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="${ROOT}/ops"
LOG="${LOG_DIR}/cn_etf_options_ingest_${STAMP}.log"
LOCK="${LOG_DIR}/cn_etf_options_ingest.lock"
TIMEFRAMES="${CN_ETF_OPTIONS_INGEST_TIMEFRAMES:-1D,1W}"

mkdir -p "${LOG_DIR}"
cd "${ROOT}"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required" >&2
  exit 2
fi
if ! docker inspect "${CONTAINER}" >/dev/null 2>&1; then
  echo "container ${CONTAINER} is not running" >&2
  exit 2
fi

exec 9>"${LOCK}"
if ! flock -n 9; then
  echo "ingest already running; skip ${STAMP}" | tee -a "${LOG}"
  exit 0
fi

echo "start ${STAMP} timeframes=${TIMEFRAMES}" | tee -a "${LOG}"
docker exec \
  -e QD_PROCESS_ROLE=celery \
  -e CN_ETF_OPTIONS_INGEST_PERSIST=1 \
  -e CN_ETF_OPTIONS_INGEST_TIMEFRAMES="${TIMEFRAMES}" \
  "${CONTAINER}" \
  python scripts/ingest_cn_etf_options_history.py --persist \
    --timeframes "${TIMEFRAMES}" \
    -o /tmp/cn_etf_options_ingest.json \
  >> "${LOG}" 2>&1
echo "done ${STAMP} exit=$?" | tee -a "${LOG}"

#!/usr/bin/env bash
# Local development setup when Docker build/run is unavailable (e.g. nested VMs
# without overlayfs). Installs PostgreSQL + Redis, configures backend .env for
# localhost, creates a Python venv, runs migrations, and prints start commands.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend_api_python"

echo "==> Installing system packages (PostgreSQL, Redis, python venv)..."
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq postgresql redis-server python3.12-venv curl
fi

echo "==> Starting PostgreSQL and Redis..."
sudo service postgresql start 2>/dev/null || true
sudo service redis-server start 2>/dev/null || true

echo "==> Creating database role and database (idempotent)..."
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='quantdinger'" | grep -q 1 \
  || sudo -u postgres psql -c "CREATE USER quantdinger WITH PASSWORD 'quantdinger123';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='quantdinger'" | grep -q 1 \
  || sudo -u postgres psql -c "CREATE DATABASE quantdinger OWNER quantdinger;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE quantdinger TO quantdinger;" >/dev/null

echo "==> Preparing backend .env..."
if [[ ! -f "$BACKEND/.env" ]]; then
  cp "$BACKEND/env.example" "$BACKEND/.env"
fi
SECRET="${SECRET_KEY:-$(python3 -c "import secrets; print(secrets.token_hex(32))")}"
CRED="${CREDENTIAL_ENCRYPTION_KEY:-$(python3 -c "import secrets; print(secrets.token_hex(32))")}"
python3 - "$BACKEND/.env" "$SECRET" "$CRED" <<'PY'
import pathlib, re, sys
path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
secret, cred = sys.argv[2], sys.argv[3]
replacements = {
    r"^SECRET_KEY=.*$": f"SECRET_KEY={secret}",
    r"^CREDENTIAL_ENCRYPTION_KEY=.*$": f"CREDENTIAL_ENCRYPTION_KEY={cred}",
    r"^DATABASE_URL=.*$": "DATABASE_URL=postgresql://quantdinger:quantdinger123@127.0.0.1:5432/quantdinger",
    r"^REDIS_HOST=.*$": "REDIS_HOST=127.0.0.1",
    r"^CELERY_REDIS_HOST=.*$": "CELERY_REDIS_HOST=127.0.0.1",
    r"^CELERY_TASKS_ENABLED=.*$": "CELERY_TASKS_ENABLED=false",
}
for pattern, value in replacements.items():
    text, n = re.subn(pattern, value, text, count=1, flags=re.M)
    if n == 0 and pattern.startswith("^SECRET_KEY"):
        text += f"\n{value}\n"
path.write_text(text, encoding="utf-8")
PY

echo "==> Creating Python virtualenv and installing dependencies..."
cd "$BACKEND"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.lock -r requirements-dev.txt -q

echo "==> Running database migrations..."
QD_PROCESS_ROLE=migration .venv/bin/python -m app.commands.migrate

cat <<EOF

Setup complete.

Start the API:
  cd $BACKEND && .venv/bin/python run.py

Verify:
  curl http://127.0.0.1:5000/api/health
  curl http://127.0.0.1:5000/api/health/ready

Run tests:
  cd $BACKEND && .venv/bin/python -m pytest tests/ -q

Notes:
  - Docker Compose remains the recommended full-stack path when overlayfs works.
  - Frontend images are pulled separately; Vue source is not in this repo.
  - Default bootstrap admin comes from ADMIN_USER / ADMIN_PASSWORD in .env.
EOF

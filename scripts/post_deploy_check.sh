#!/usr/bin/env bash
#
# ChoreDown post-deploy smoke test — run this ON THE PROXMOX BOX after a deploy.
#
#   cd /opt/choredown && ./scripts/post_deploy_check.sh
#
# It loads your .env, then verifies the four things that actually break a deploy:
#   1. Django config is valid          (manage.py check)
#   2. No migrations are missing        (the #1 cause of "buttons error out")
#   3. Static files are collected       (so CSS/JS load)
#   4. The running app answers on :8000  (the service is actually up)
#
# Add --with-tests to also run the suite against a throwaway SQLite DB.
set -euo pipefail
cd "$(dirname "$0")/.."

# Load .env if present (so DATABASE_URL etc. are set for management commands).
if [ -f .env ]; then set -a; . ./.env; set +a; fi
# Activate the virtualenv if it exists at the conventional path.
if [ -f venv/bin/activate ]; then source venv/bin/activate; fi

pass() { printf '  \033[32m✓\033[0m %s\n' "$1"; }
fail() { printf '  \033[31m✗ %s\033[0m\n' "$1"; exit 1; }

echo "==> 1/4 Django system check"
python manage.py check >/dev/null && pass "config valid" || fail "manage.py check failed"

echo "==> 2/4 Migrations applied"
if python manage.py migrate --check >/dev/null 2>&1; then
  pass "schema up to date"
else
  fail "UNAPPLIED MIGRATIONS — run: python manage.py migrate"
fi

echo "==> 3/4 Static files collected"
if python manage.py collectstatic --noinput >/dev/null 2>&1; then
  pass "static files OK"
else
  fail "collectstatic failed"
fi

if [ "${1:-}" = "--with-tests" ]; then
  echo "==> (extra) Test suite on throwaway SQLite"
  DATABASE_URL="sqlite:///deploy_check.sqlite3" python manage.py test --noinput \
    && { pass "tests passed"; rm -f deploy_check.sqlite3; } \
    || { rm -f deploy_check.sqlite3; fail "tests failed"; }
fi

echo "==> 4/4 HTTP health check (http://127.0.0.1:8000/)"
code=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/ || echo 000)
if [ "$code" = "200" ] || [ "$code" = "302" ]; then
  pass "app responding ($code)"
else
  fail "app not responding on :8000 ($code) — is the choredown service running? (sudo systemctl status choredown)"
fi

printf '\n\033[32mAll post-deploy checks passed.\033[0m\n'

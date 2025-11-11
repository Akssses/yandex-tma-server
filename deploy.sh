#!/usr/bin/env bash
set -euo pipefail

# Configuration (override via env or edit below)
APP_DIR="${APP_DIR:-/opt/yandextma}"
REPO_DIR="${REPO_DIR:-$APP_DIR/repo}"
VENV_DIR="${VENV_DIR:-$APP_DIR/venv}"
SERVICE_NAME="${SERVICE_NAME:-yandextma}"
PYTHON="${PYTHON:-python3}"

echo "Deploy starting..."
echo "APP_DIR=$APP_DIR"
echo "REPO_DIR=$REPO_DIR"
echo "VENV_DIR=$VENV_DIR"
echo "SERVICE_NAME=$SERVICE_NAME"

if [ ! -d "$REPO_DIR/.git" ]; then
  echo "Repository directory $REPO_DIR missing. Run bootstrap steps first."
  exit 1
fi

cd "$REPO_DIR"
git fetch --all --prune

# Optionally pass branch/tag via first arg
REF="${1:-main}"
git checkout "$REF"
git pull --ff-only origin "$REF" || true

# Backend lives in 'server'
cd server

if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON" -m venv "$VENV_DIR"
fi
. "$VENV_DIR/bin/activate"

pip install --upgrade pip
pip install -r requirements.txt

export DJANGO_SETTINGS_MODULE=core.settings
export PYTHONPATH="$(pwd)"

python manage.py migrate --noinput
python manage.py collectstatic --noinput

sudo systemctl restart "${SERVICE_NAME}.service"

echo "Deploy completed."



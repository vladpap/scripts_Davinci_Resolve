#!/bin/zsh

set -euo pipefail

PROJECT_DIR="${0:A:h}"
PYTHON="$PROJECT_DIR/.venv/bin/python"
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

if [[ "$(uname -s)" != "Darwin" ]]; then
  print -u2 "Ошибка: скрипт запуска предназначен только для macOS."
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  print -u2 "Не найден npm. Сначала запустите install.command."
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  print -u2 "Не найден uv. Сначала запустите install.command."
  exit 1
fi

if [[ ! -x "$PYTHON" ]]; then
  print -u2 "Не найдено окружение Python. Сначала запустите install.command."
  exit 1
fi

if [[ "$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')" != "3.11" ]]; then
  print -u2 "Окружение создано не на Python 3.11. Сначала запустите install.command."
  exit 1
fi

if ! "$PYTHON" -c 'import fastapi, uvicorn, yaml' >/dev/null 2>&1; then
  print -u2 "Не найдены зависимости серверной части. Сначала запустите install.command."
  exit 1
fi

if [[ ! -x "$PROJECT_DIR/frontend/node_modules/.bin/vite" ]]; then
  print -u2 "Не найдены зависимости интерфейса. Сначала запустите install.command."
  exit 1
fi

cd "$PROJECT_DIR"

print "Запускается серверная часть: http://127.0.0.1:8765"
"$PYTHON" -m uvicorn backend.main:app --host 127.0.0.1 --port 8765 &
BACKEND_PID=$!

print "Запускается интерфейс. Его адрес появится ниже."
(cd frontend && npm run dev -- --host 127.0.0.1) &
FRONTEND_PID=$!

cleanup() {
  print "\nОстанавливается панель…"
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}

trap cleanup EXIT INT TERM
wait

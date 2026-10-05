#!/bin/zsh

set -euo pipefail

PROJECT_DIR="${0:A:h}"
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

print "Проверка окружения панели DaVinci Resolve…"

if [[ "$(uname -s)" != "Darwin" ]]; then
  print -u2 "Ошибка: установщик предназначен только для macOS."
  exit 1
fi

if ! xcode-select -p >/dev/null 2>&1; then
  print "Устанавливаются инструменты командной строки Xcode. Завершите установку в открывшемся окне и повторите запуск install.command."
  xcode-select --install || true
  exit 1
fi

if ! command -v brew >/dev/null 2>&1; then
  print "Устанавливается Homebrew для Node.js…"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  if [[ -x /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [[ -x /usr/local/bin/brew ]]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
fi

if ! command -v npm >/dev/null 2>&1; then
  print "Устанавливается Node.js и npm…"
  brew install node
fi

if ! command -v uv >/dev/null 2>&1; then
  print "Устанавливается uv…"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi

if ! command -v uv >/dev/null 2>&1; then
  print -u2 "Ошибка: не удалось найти uv после установки. Откройте новое окно Терминала и запустите install.command снова."
  exit 1
fi

cd "$PROJECT_DIR"

print "Устанавливается Python 3.11 через uv…"
uv python install 3.11

print "Создаётся виртуальное окружение Python…"
uv venv --python 3.11 .venv

print "Устанавливаются зависимости серверной части…"
uv pip sync --python .venv/bin/python requirements.txt

print "Устанавливаются зависимости интерфейса…"
npm ci --prefix frontend

print "Установка завершена. Запускается панель…"
exec "$PROJECT_DIR/start.command"

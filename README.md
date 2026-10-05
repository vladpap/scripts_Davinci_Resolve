# Панель управления DaVinci Resolve

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-8-646CFF?logo=vite&logoColor=white)
![Tailwind%20CSS](https://img.shields.io/badge/Tailwind%20CSS-4-06B6D4?logo=tailwindcss&logoColor=white)
![macOS](https://img.shields.io/badge/macOS-supported-000000?logo=apple&logoColor=white)

Локальная веб-панель для запуска Python-скриптов DaVinci Resolve. Сервер
принимает подключения только на `127.0.0.1` и использует API запущенного
DaVinci Resolve.

## Быстрый запуск в macOS

В Терминале перейдите в каталог проекта и выполните один раз:

```zsh
./install.command
```

Скрипт проверит macOS, установит при необходимости инструменты командной строки
Xcode, Homebrew, Node.js/npm, `uv` и Python 3.11. Затем он создаст окружение
Python, установит зависимости серверной части и интерфейса и запустит панель.

Для следующих запусков используйте:

```zsh
./start.command
```

`start.command` только проверяет уже установленное окружение и запускает
backend и frontend. Для остановки панели нажмите `Ctrl+C` в том же окне
Терминала.

## Запуск серверной части

Выполняйте команды из корня клонированного репозитория:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8765
```

Откройте <http://127.0.0.1:8765/api/health>, чтобы проверить состояние
подключения к Resolve.

## Разработка интерфейса

Из корня репозитория перейдите в каталог интерфейса:

```bash
cd frontend
npm install
npm run dev
```

Сервер разработки Vite запускает React-интерфейс. Во время разработки запросы,
начинающиеся с `/api`, проксируются к серверной части на порт `8765`.

## Контракт API

### `GET /api/health`

Проверяет текущее подключение к DaVinci Resolve. Ошибка импорта, недоступный
экземпляр Resolve или устаревшее подключение возвращают успешный HTTP-ответ с
`resolve_connected: false`; следующий запрос снова попробует подключиться.

```json
{
  "resolve_connected": true,
  "version": "20.0.1.3"
}
```

Когда Resolve недоступен, ответ выглядит так:

```json
{
  "resolve_connected": false,
  "version": ""
}
```

### `GET /api/project-dashboard`

Возвращает сводку по открытому в Resolve проекту. `media_count` включает
элементы всех папок Media Pool. `missing_clip_count` содержит число клипов с
исходным абсолютным путём к файлу, которого больше нет на диске.

```json
{
  "resolve_connected": true,
  "project_name": "Рекламный монтаж",
  "media_count": 248,
  "timeline_name": "Сборка v4",
  "timeline_count": 6,
  "missing_clip_count": 2
}
```

### `GET /api/scripts`

Возвращает метаданные всех корректных Python-файлов из `backend/scripts/`.
Скрипты обнаруживаются при запуске сервера, поэтому после добавления или
изменения скрипта серверную часть нужно перезапустить. При обнаружении файлы разбираются
через `ast`, но не импортируются и не выполняются.

```json
[
  {
    "id": "add_markers",
    "name": "Добавить маркеры на таймлинию",
    "description": "Добавляет маркер в начале каждого клипа на выбранной дорожке.",
    "params": [
      {
        "name": "color",
        "type": "select",
        "default": "Red",
        "options": ["Red", "Blue", "Green"]
      }
    ]
  }
]
```

### `GET /api/scripts/{id}`

Возвращает манифест одного скрипта. Для неизвестного идентификатора возвращается
`404`.

### `POST /api/scripts/{id}/run`

Проверяет значения формы по манифесту выбранного скрипта и ставит выполнение в
выделенный рабочий поток. Resolve должен быть подключён, иначе конечная точка вернёт
`503`. Неизвестные значения и неверные типы параметров возвращают `422`.

```json
{
  "params": {
    "track_type": "video",
    "track_index": 1,
    "color": "Blue",
    "note": "Проверка"
  }
}
```

При успешном принятии запроса возвращается `202 Accepted`:

```json
{
  "run_id": "dfacb6f5e3b7470bb9e401c7b4373a73",
  "status": "queued"
}
```

Эта конечная точка подтверждает только принятие запуска. Завершение, ошибки,
остановка и поток логов доступны через WebSocket ниже.

### `POST /api/runs/{run_id}/stop`

Отменяет ожидающий запуск и возвращает его итоговый статус `cancelled`. Python
не может безопасно остановить синхронную функцию, уже выполняющуюся в другом
потоке, поэтому запущенный скрипт вернёт `409 Conflict` и завершится штатно.

### `WS /ws/logs/{run_id}`

Передаёт JSON-события одного принятого запуска: статусы `queued`, `running` и
итоговые (`success`, `error` или `cancelled`), стандартный вывод скрипта,
исключения и краткий результат. События, созданные до подключения WebSocket,
передаются первыми.

## Манифест скрипта

Каждый файл `.py` в `backend/scripts/` должен содержать YAML-документ в первой
строке документации модуля. Имя файла становится API-идентификатором и должно состоять из
строчных латинских букв, цифр и `_`. Поддерживаются типы параметров `text`,
`number`, `select`, `bool`, `textarea` и `file`. Параметр `select` должен
задавать непустой список `options`, а его `default` должен быть одним из них.

```python
"""
name: Пример скрипта
description: Краткое описание скрипта для панели.
params:
  - name: note
    type: text
    default: Привет
"""

def run(resolve, params):
    pass
```

## Структура проекта

```text
backend/
  main.py            # FastAPI-приложение и конечные точки API
  resolve_bridge.py  # синхронный адаптер API DaVinci Resolve
  script_loader.py   # разбор манифестов и реестр скриптов
  runner.py          # проверенное фоновое выполнение скриптов
  scripts/           # пользовательские скрипты и их YAML-манифесты
frontend/
  src/components/ui/ # локальная основа компонентов shadcn/ui
  src/lib/           # общие утилиты интерфейса
```

## Лицензия

Проект распространяется по лицензии [MIT](LICENSE). Разрешены использование,
изменение и распространение при сохранении уведомления об авторских правах и
текста лицензии.

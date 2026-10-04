# Создание скриптов и веб-элементов

Эта папка содержит Python-скрипты, которые панель запускает в DaVinci Resolve.
Каждый файл `*.py` с корректным манифестом автоматически появляется в разделе
«Скрипты» после перезапуска backend.

> Файлы, начинающиеся с `_`, не регистрируются. Этот `README.md` также
> игнорируется: панель загружает только Python-файлы.

## 1. Создание скрипта для DaVinci Resolve

### Шаг 1. Создайте файл

Добавьте файл с именем в нижнем регистре: `my_script.py`.

Имя файла становится идентификатором скрипта в API. Допускаются латинские
строчные буквы, цифры и `_`; имя должно начинаться с буквы.

Подходящие имена:

```text
create_markers.py
export_audio_2.py
```

Неподходящие имена:

```text
Export Timeline.py
2_export.py
create-markers.py
```

### Шаг 2. Добавьте манифест в docstring модуля

Первый docstring файла должен содержать YAML-манифест. Он задаёт название,
описание и поля формы в веб-панели.

```python
"""
name: Example Timeline Script
description: Выводит название активной временной шкалы.
params:
  - name: include_markers
    type: bool
    default: true
"""
```

Обязательное поле — `name`. Поле `description` необязательно. Если параметров
нет, можно указать `params: []` или вовсе не добавлять `params`.

### Шаг 3. Реализуйте `run(resolve, params)`

Панель импортирует модуль только в момент запуска и вызывает функцию
`run(resolve, params)`. В `resolve` передаётся подключённый объект DaVinci
Resolve API, а в `params` — проверенные значения из формы.

```python
"""
name: Timeline Name
description: Возвращает название текущей временной шкалы.
"""

from __future__ import annotations

from typing import Any, Dict


def run(resolve: Any, params: Dict[str, Any]) -> Dict[str, str]:
    project_manager = resolve.GetProjectManager()
    project = project_manager.GetCurrentProject() if project_manager else None
    timeline = project.GetCurrentTimeline() if project else None
    if timeline is None:
        raise RuntimeError("Откройте проект и выберите временную шкалу.")

    print(f"Обработка таймлайна: {timeline.GetName()}")
    return {"timeline_name": timeline.GetName()}
```

`print()` и сообщения в `stderr` передаются в блок «Логи выполнения» через
WebSocket. Возвращаемое значение отображается в логах как краткий результат.
Исключение останавливает запуск со статусом `error` и показывает traceback.

### Типы параметров и соответствующие элементы формы

| `type` | Элемент веб-интерфейса | Пример значения |
| --- | --- | --- |
| `text` | однострочное текстовое поле | `Review` |
| `number` | числовое поле | `1` |
| `select` | выпадающий список | `Blue` |
| `bool` | checkbox | `true` |
| `textarea` | многострочное поле | `Описание операции` |
| `file` | текстовое поле для пути | `~/Desktop/result.json` |

Пример манифеста, содержащего все типы:

```python
"""
name: All Parameters Example
description: Пример полей динамической формы.
params:
  - name: title
    type: text
    default: Новая задача
  - name: track_index
    type: number
    default: 1
  - name: marker_color
    type: select
    options: [Red, Blue, Green]
    default: Blue
  - name: enabled
    type: bool
    default: true
  - name: note
    type: textarea
    default: Текст заметки
  - name: output_path
    type: file
    default: ~/Desktop/export.json
"""
```

Для `select` обязательны непустой список `options` и `default`, совпадающий с
одним из значений списка. Имена параметров могут содержать только латинские
буквы, цифры и `_`, начинаясь с буквы.

### Шаг 4. Перезапустите backend

Список скриптов считывается при запуске сервера. После добавления или изменения
файла перезапустите backend:

```bash
cd resolve-panel
uvicorn backend.main:app --host 127.0.0.1 --port 8765
```

Откройте панель и обновите список скриптов. Некорректный манифест не ломает
сервер: такой файл будет пропущен, а причина появится в логах backend.

### Выполнение и ограничения

- Скрипт выполняется в отдельном рабочем потоке, поэтому HTTP- и WebSocket-
  обработчики остаются отзывчивыми.
- Одновременно разрешён только один запуск. Пока скрипт выполняется, новый
  запуск получает ошибку `409 Conflict` и не добавляется в очередь.
- Принудительно остановить уже выполняющуюся синхронную Python-функцию небезопасно.
  Поэтому скрипт должен периодически проверять собственные условия остановки,
  если в нём выполняется длительная работа.
- Всегда проверяйте, что `project`, `timeline`, `clip` и другие объекты Resolve
  существуют, прежде чем вызывать их методы.

## 2. Создание веб-элементов интерфейса

Веб-интерфейс находится не в этой папке, а в `frontend/src/`. Примеры всех
доступных элементов собраны в разделе панели «Примеры UI» и реализованы в
`frontend/src/components/UiShowcase.tsx`.

### Используйте существующие базовые компоненты

Перед созданием нового элемента проверьте локальные компоненты:

```text
frontend/src/components/ui/button.tsx  # Button
frontend/src/components/ui/card.tsx    # Card, CardHeader, CardContent
frontend/src/components/ui/toast.tsx   # ToastProvider и useToast
```

Пример карточки с кнопкой и уведомлением:

```tsx
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useToast } from '@/lib/toast'

function ExampleCard() {
  const { toast } = useToast()

  return (
    <Card>
      <CardHeader>
        <CardTitle>Пример действия</CardTitle>
      </CardHeader>
      <CardContent>
        <Button onClick={() => toast({ title: 'Готово', variant: 'success' })}>
          Выполнить
        </Button>
      </CardContent>
    </Card>
  )
}
```

### Стили и цветовые токены

Используйте Tailwind-классы и общие токены темы, а не жёстко заданные цвета:

```tsx
<div className="rounded-lg border border-border bg-card text-card-foreground">
  <p className="text-muted-foreground">Второстепенный текст</p>
  <Button>Основное действие</Button>
</div>
```

Основные токены: `bg-background`, `bg-card`, `bg-muted`, `text-foreground`,
`text-muted-foreground`, `border-border`, `border-input`, `bg-primary`,
`text-primary-foreground` и `focus:ring-ring`.

Для полей формы соблюдайте уже используемый стиль:

```tsx
<label className="text-sm font-medium" htmlFor="task-name">Название</label>
<input
  className="mt-2 h-9 w-full rounded-md border border-input bg-muted/30 px-3 text-sm outline-none placeholder:text-muted-foreground focus:ring-2 focus:ring-ring"
  id="task-name"
  placeholder="Введите название"
/>
```

### Добавление элемента в витрину UI

1. Откройте `frontend/src/components/UiShowcase.tsx`.
2. Добавьте новый пример внутри `ShowcaseCard` либо создайте новую карточку.
3. Для интерактивного состояния используйте `useState`.
4. Проверьте, что у полей есть `label`, а у иконок-кнопок — `aria-label`.
5. Запустите проверку:

   ```bash
   cd resolve-panel/frontend
   npm run build && npm run lint
   ```

Не создавайте вторую палитру или отдельный набор кнопок без необходимости:
повторно используйте локальные `Button`, `Card` и общие токены темы.

## Полезные примеры

- `add_markers.py` — параметры `select`, `number` и `text`, работа с клипами и
  добавление маркеров.
- `export_timeline.py` — параметры `file` и `bool`, запись JSON-файла и
  безопасная обработка текущей временной шкалы.
- `frontend/src/components/ParamForm.tsx` — преобразование типов параметров
  манифеста в веб-поля.
- `frontend/src/components/UiShowcase.tsx` — интерактивные примеры элементов
  веб-интерфейса.

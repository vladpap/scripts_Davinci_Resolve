# Интерфейс панели DaVinci Resolve

React-интерфейс панели управления DaVinci Resolve, собранный с Vite,
TypeScript и Tailwind CSS.

## Запуск в режиме разработки

```bash
cd resolve-panel/frontend
npm install
npm run dev
```

Vite выведет локальный адрес интерфейса. Запросы к `/api` автоматически
проксируются на серверную часть по адресу `http://127.0.0.1:8765`, поэтому её
нужно запустить отдельно.

## Проверка и итоговая сборка

```bash
npm run build
npm run lint
```

`npm run build` выполняет проверку TypeScript и создаёт итоговую сборку в
каталоге `dist/`. `npm run lint` запускает Oxlint.

## Структура исходного кода

```text
src/
  App.tsx              # основной экран, загрузка данных панели и навигация
  components/          # компоненты интерфейса и формы скриптов
  components/ui/       # базовые локальные компоненты интерфейса
  lib/api.ts           # запросы к серверному API
  lib/scripts.ts       # TypeScript-типы API скриптов и Resolve
  lib/toast.ts         # уведомления
```

Для новых компонентов используйте существующие `Button`, `Card`, общие токены
темы и классы Tailwind. Дополнительные рекомендации находятся в
[`../backend/scripts/README.md`](../backend/scripts/README.md).

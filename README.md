# Lunar Dream Calendar (Graphite Night)

Статический сайт: лунный календарь снов + современный сонник + клиентский разбор сна.

## Next.js фронтенд (Phase 1)
- `frontend/` — приложение на Next.js 14 (App Router) с компонентом `LunarWidget`.
- `frontend/app/(calendar)/page.tsx` перенаправляет на локализованные маршруты `/en/calendar` и `/ru/calendar`.
- `frontend/components/LunarWidget.tsx` — интерактивный виджет (анимации, локализация, кеширование).
- `frontend/__tests__/` — unit-тесты (Jest + Testing Library).
- `frontend/e2e/` — E2E тест (Playwright) для сценария раскрытия календаря.
- `frontend/stories/` — Storybook-пример для визуальной проверки.
- Запуск: `cd frontend && npm install && npm run dev`.
- Прод билд: `npm run build && npm run start` (используется в Render).
- Подробная инструкция по деплою: [docs/deployment-render.md](docs/deployment-render.md).

## Backend API
- `backend/app/main.py` — FastAPI эндпоинт `/lunar?date=YYYY-MM-DD&locale=en&tz=Europe/Moscow`.
- Возвращает фазу Луны, номер лунного дня, описание и рекомендации (RU/EN).
- Запуск: `uvicorn backend.app.main:app --reload`.

## Быстрый старт (GitHub Pages)
1. Склонируйте репозиторий или загрузите файлы.
2. Убедитесь, что есть `data/dreams_curated.json` (можно с примерами).
3. Включите Pages: Settings → Pages → Branch: `main` → `/ (root)`.
4. Откройте: `https://<username>.github.io/oneiro-scope/`.

## Структура
- `index.html` — разметка.
- `styles/*` — тема Graphite Night.
- `scripts/calendar.js` — календарь, луна, локали.
- `scripts/dreambook.js` — поиск по соннику и «Разбор сна».
- `data/dreams_curated.json` — набор символов (обновляйте ETL-скриптами).

## Настройка
- Язык берётся из браузера, можно переключить селектором.
- Часовой пояс — авто/список.
- Иконка луны — монохромный SVG-серп, фаза рассчитывается приближённо.

## Данные
`data/dreams_curated.json` можно обновлять вручную или через CI.

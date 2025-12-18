# Задание для следующей сессии

## Контекст
Сессия 2025-12-18 завершена успешно. Все критические build/deploy проблемы исправлены.
Проект готов к production деплою на Render.

**Branch:** `claude/continue-oneiroscope-LgRZe` (9 коммитов)

## Приоритет 1: Проверка Production Deploy

### Задача
После успешного деплоя на Render, необходимо проверить что всё работает в live окружении.

### Что проверить:

1. **Backend логи**
   - Открыть Render dashboard → backend logs
   - Проверить что в логах: `Environment: production`
   - Проверить что НЕТ строки: `Initializing database...` на старте
   - Если есть `init_db()` - значит `ENVIRONMENT` не применился

2. **Frontend build**
   - Проверить что frontend успешно собрался
   - Проверить что нет ошибок типов TypeScript
   - Проверить что CI/CD тесты прошли (зелёные)

3. **Live тестирование UI**
   - Открыть live URL фронтенда
   - ✅ Проверить что favicon загружается (луна с звёздами)
   - ✅ Проверить Header (логотип OneiroScope, навигация)
   - ✅ Проверить что клик на "Главная" ведёт на home page
   - ✅ Проверить лунный календарь (`/calendar`)
   - ✅ Проверить Timezone Selector - должен загружать 19 timezone
   - ✅ Проверить что смена timezone обновляет данные

4. **API Endpoints**
   ```bash
   # Проверить endpoints работают
   curl https://<backend-url>/health
   curl https://<backend-url>/api/v1/lunar/lunar?date=2025-12-18&locale=ru
   curl https://<backend-url>/api/v1/lunar/timezones
   ```

## Приоритет 2: Исправить Backend Pytest (P0)

### Проблема
`backend/tests/test_astrology_quality.py` импортирует несуществующие модули:
```python
from backend.services.astrology.engine import ...
```

Эти модули не существуют в текущей архитектуре.

### Что сделать:
1. Прочитать `backend/tests/test_astrology_quality.py`
2. Понять какие тесты пытается делать
3. Обновить импорты под текущую структуру:
   - `backend.services.astrology.service`
   - `backend.services.astrology.natal_chart`
   - `backend.services.astrology.transits`
   - и т.д.
4. Запустить `pytest backend/tests` и проверить что проходит

### Acceptance Criteria:
- `pytest backend/tests` проходит без ImportError
- CI/CD backend tests зелёные

## Приоритет 3: Добавить переключатель языка

### Задача
Добавить возможность переключения RU/EN в Header компоненте.

### Требования:
1. Кнопка/dropdown в Header справа от навигации
2. При клике переключает язык через next-intl
3. Сохраняет выбор в localStorage
4. Перенаправляет на `/ru/...` или `/en/...`

### Файлы для изменения:
- `frontend/components/Header.tsx` - добавить LanguageSwitcher
- `frontend/components/LanguageSwitcher.tsx` - новый компонент (опционально)
- `frontend/messages/ru.json` и `en.json` - добавить переводы для switcher

## Приоритет 4: Улучшения UX (опционально)

### Loading States
- Добавить skeleton loader для LunarWidget
- Добавить spinner для timezone selector загрузки

### Error Handling
- Добавить retry логику в LunarWidget для failed month load
- Показывать более информативные ошибки

### Mobile Responsive
- Протестировать на мобильных разрешениях
- Улучшить Header для mobile (hamburger menu?)

## Справочная информация

### Полезные документы:
- [CLAUDE.md](../CLAUDE.md) - Project guide
- [REPO_AUDIT.md](./REPO_AUDIT.md) - Технический аудит
- [SESSION_SUMMARY_2025-12-18.md](./SESSION_SUMMARY_2025-12-18.md) - Что было сделано сегодня
- [SESSION_SUMMARY_2025-12-17.md](./SESSION_SUMMARY_2025-12-17.md) - Предыдущая сессия

### Коммиты текущей сессии:
```
09706e2 - fix: add missing timezone field to LunarDayPayload type
96ea83d - refactor: make .gitignore rules more specific
d3f9160 - fix: add missing /api/timezones proxy endpoint
03c31b8 - feat: add navigation header, favicon and branding
1001b9f - fix: set ENVIRONMENT=production for backend in Render
7a83f34 - fix: add TransformStream polyfill and timezone to tests
5cbb05c - fix: resolve workflow YAML syntax and Playwright error
2df71ed - fix: exclude e2e tests from Jest test runner
853aa73 - fix: update Jest mocks and lunar-math test expectations
```

### Render Environment Variables (проверить):
- Backend: `ENVIRONMENT=production` ✅
- Backend: `LUNAR_DEFAULT_TZ=Europe/Moscow` ✅
- Backend: `GEONAMES_USERNAME` (нужен для геокодинга)
- Backend: `ALLOWED_ORIGINS` = frontend URL
- Frontend: `NEXT_PUBLIC_API_URL` = backend URL
- Frontend: `NEXT_PUBLIC_LUNAR_API_URL` = backend URL

---

## Начало следующей сессии

1. Проверить текущий статус CI/CD (все ли тесты зелёные)
2. Проверить Render deploy status
3. Если всё зелёное → начать с Приоритет 1 (проверка production)
4. Если есть проблемы → сначала их исправить

**Важно:** Перед началом работы прочитать:
- `docs/SESSION_SUMMARY_2025-12-18.md`
- `CLAUDE.md` (секция "Next Actions")

# Отчет о расследовании состояния проекта OneiroScope
**Дата:** 2025-12-17
**Ветка:** `claude/analyze-fix-frontend-PXk9Y`
**Коммит:** `d61202b`

---

## 🔍 Резюме расследования

Проведен полный анализ репозитория после попытки установки claude-mem и отката деплоя. Обнаружено несколько критических проблем с фронтендом и структурой проекта.

---

## ❌ 1. Claude-mem - НЕ УСТАНОВЛЕН

### Результаты проверки:
```
✗ ~/.claude/plugins/marketplaces/ - директория не найдена
✗ claude-mem worker процесс - не запущен
✗ http://localhost:37777/api/health - не отвечает
```

### Вывод:
**Claude-mem НЕ установлен.** Установка через `/plugin` команды не была выполнена.

### Рекомендация:
Выполнить установку в терминале Claude Code:
```bash
/plugin marketplace add thedotmack/claude-mem
/plugin install claude-mem
```
Затем перезапустить Claude Code.

---

## 🔴 2. Frontend - КРИТИЧЕСКИЕ ПРОБЛЕМЫ

### 2.1 Server Components Render Error

**Ошибка в консоли браузера:**
```
Error: An error occurred in the Server Components render.
The specific message is omitted in production builds to avoid leaking sensitive details.
```

### 2.2 Node Modules - ОТСУТСТВУЮТ

```bash
$ cd frontend && npm run build
> next build
sh: 1: next: not found
```

**Проблема:** `frontend/node_modules/` не существует!

### 2.3 Конфликт Layout файлов

Обнаружен **ДУБЛИКАТ корневого layout**:

```
frontend/app/layout.tsx           ← Рендерит <html>
frontend/app/[locale]/layout.tsx  ← Тоже рендерит <html>
```

**Это вызывает конфликт в Next.js App Router!**

Оба файла создают `<html>` тег, что приводит к Server Components ошибке.

#### `frontend/app/layout.tsx` (должен быть удален):
```tsx
export default function RootLayout({children}: {children: React.ReactNode}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

#### `frontend/app/[locale]/layout.tsx` (правильный):
```tsx
export default async function LocaleLayout({children, params}) {
  return (
    <html lang={locale}>
      <body className="bg-bg text-ink antialiased">
        <NextIntlClientProvider locale={locale} messages={messages}>
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
```

### 2.4 Структура страниц

**Найдены дубликаты:**
```
frontend/app/(calendar)/page.tsx                    ← Редирект на /en/calendar
frontend/app/[locale]/(calendar)/calendar/page.tsx  ← Основная страница календаря
```

**Текущие страницы:**
- `frontend/app/[locale]/page.tsx` - главная страница (клиентский компонент)
- `frontend/app/[locale]/astrology/page.tsx` - астрология
- `frontend/app/[locale]/dreams/page.tsx` - сны
- `frontend/app/[locale]/(calendar)/calendar/page.tsx` - календарь

---

## 📊 3. Git История и Откат

### 3.1 Текущее состояние:
```
HEAD: d61202b - docs: add project cleanup plan
Branch: claude/analyze-fix-frontend-PXk9Y
Remote: origin/claude/analyze-fix-frontend-PXk9Y
Working tree: clean
```

### 3.2 Недавние коммиты (последние 2 дня):
```
d61202b - docs: add project cleanup plan for frontend structure issues
a4ff430 - Merge pull request #42 (Create OneiroScope landing page) ← Codex
9ef9eb1 - ci: update repository inventory
ca1d9e3 - Create OneiroScope landing page ← ЗДЕСЬ СОЗДАН ЛЕНДИНГ
dd5163e - Merge pull request #41 (Fix lunar stub)
0a8ecdb - Fix lunar stub to vary lunar day by date
```

### 3.3 Git Reflog:
```
d61202b HEAD@{0}: commit: docs: add project cleanup plan
a4ff430 HEAD@{1}: checkout: moving to claude/analyze-fix-frontend-PXk9Y
a4ff430 HEAD@{2}: checkout: moving from master to FETCH_HEAD
```

**Вывод:** Откат был выполнен на коммит `a4ff430`, но landing page файлы остались.

---

## 🗂️ 4. Проблемы со структурой проекта

### 4.1 Файлы в корневой папке (не должны быть там):

#### Landing Page (создан Codex в PR #42):
```
/index.html           ← HTML landing page
/styles/              ← CSS стили
  ├── site.css
  └── tokens.css
```

#### Python файлы (дубликаты библиотек):
```
/swisseph.py          ← Swiss Ephemeris модуль
/timezonefinder.py    ← Timezone finder
/geopy/               ← Geocoding библиотека
/pandas/              ← Pandas библиотека
```

#### Тесты (должны быть в backend/tests):
```
/tests/
  ├── conftest.py
  └── test_integration_dreamy_swisseph.py
```

#### Пустые папки:
```
/oneiro-scope/        ← Пустая папка
```

### 4.2 Backend - В ПОРЯДКЕ

```bash
$ ls backend/
✓ api/       - API endpoints (v1/lunar, v1/astrology, v1/dreams, v1/health)
✓ app/       - FastAPI app entry point
✓ core/      - Config, database, LLM provider
✓ services/  - Lunar, astrology, dreams services
✓ models/    - ORM models
✓ data/      - lunar_tables.json
✓ alembic/   - Database migrations
```

**Backend структура правильная!**

---

## 🎯 5. Критические проблемы из REPO_AUDIT.md

### P0 (Блокеры):

#### 5.1 Astrology Geocoder - await на синхронном методе ✅ ИСПРАВЛЕНО
```python
# backend/services/astrology/geocoder.py:59-86
def geocode(self, query: str) -> GeoLocation:  # ← Синхронный метод
    # ...работает синхронно
```

**Статус:** Исправлено в PR #39 (`d000514 - Handle geocoding errors synchronously`)

#### 5.2 Backend тесты - Импорт несуществующих модулей ⚠️ НЕ ИСПРАВЛЕНО
```python
# backend/tests/test_astrology_quality.py:5-10
from backend.services.astrology.engine.aspects import ...  # ← НЕ СУЩЕСТВУЕТ
```

**Проблема:** Тесты ссылаются на старую структуру модулей.

### P1 (Важные):

#### 5.3 Render ENVIRONMENT=development ⚠️ ТРЕБУЕТ ВНИМАНИЯ
```python
# backend/core/config.py
ENVIRONMENT = "development"  # ← По умолчанию dev режим
```

**Проблема:** На Render запускается в dev mode → auto `init_db()` в проде.

---

## 🔧 6. Render Deployment

### 6.1 Сервисы (из render.yaml):
```yaml
- name: oneiroscope-backend        ← FastAPI backend
- name: oneiroscope-frontend       ← Next.js frontend
- name: oneiroscope-postgres       ← PostgreSQL DB
- name: oneiroscope-redis          ← Redis cache
```

### 6.2 Проблемы с environment variables:
```
NEXT_PUBLIC_API_URL    - должен быть из backend RENDER_EXTERNAL_URL
LUNAR_API_URL          - должен быть из backend RENDER_EXTERNAL_URL
ALLOWED_ORIGINS        - должен содержать frontend URL со схемой (https://)
ENVIRONMENT            - должен быть "production" для Render
```

---

## 🚨 7. Срочные действия

### Шаг 1: Исправить Frontend Layout ⚠️ КРИТИЧНО

**Проблема:** Дубликат `<html>` тега вызывает Server Components error.

**Решение:**
```bash
# Удалить корневой layout (он не нужен с next-intl)
rm frontend/app/layout.tsx

# Оставить только локализованный layout
# frontend/app/[locale]/layout.tsx - уже правильный
```

### Шаг 2: Установить зависимости Frontend

```bash
cd frontend
npm ci
npm run build  # Проверить сборку
```

### Шаг 3: Очистить структуру проекта

**Вариант A** - Переместить landing в frontend:
```bash
mkdir -p frontend/public/landing
mv index.html frontend/public/landing/
mv styles frontend/public/landing/
```

**Вариант B** - Удалить landing (если не нужен):
```bash
rm index.html
rm -rf styles/
```

**Очистить Python файлы:**
```bash
# Переместить тесты
mv tests/conftest.py backend/tests/
mv tests/test_integration_dreamy_swisseph.py backend/tests/
rmdir tests

# Удалить дубликаты библиотек
rm swisseph.py timezonefinder.py
rm -rf geopy/ pandas/

# Удалить пустую папку
rmdir oneiro-scope/
```

### Шаг 4: Исправить Backend тесты

```bash
# Обновить импорты в тестах
cd backend/tests
# Заменить старые импорты на актуальные модули
```

### Шаг 5: Настроить Render переменные

В Render Dashboard → Backend Service → Environment:
```
ENVIRONMENT=production
ALLOWED_ORIGINS=https://<frontend-url>.onrender.com
```

В Render Dashboard → Frontend Service → Environment:
```
NEXT_PUBLIC_API_URL=https://<backend-url>.onrender.com
LUNAR_API_URL=https://<backend-url>.onrender.com
```

Затем: **Clear build cache & Deploy** для frontend.

---

## 📋 8. Чеклист исправлений

### Критические (исправить сейчас):
- [ ] ❌ Удалить `frontend/app/layout.tsx` (дубликат)
- [ ] ❌ Установить `frontend/node_modules` (`npm ci`)
- [ ] ❌ Проверить сборку frontend (`npm run build`)

### Важные (следующий приоритет):
- [ ] ⚠️ Принять решение по landing page (переместить/удалить)
- [ ] ⚠️ Очистить Python файлы из корня
- [ ] ⚠️ Переместить тесты в `backend/tests/`
- [ ] ⚠️ Исправить импорты в backend тестах

### Настройки Render:
- [ ] ⚠️ Выставить `ENVIRONMENT=production` на backend
- [ ] ⚠️ Настроить `ALLOWED_ORIGINS` со схемой (https://)
- [ ] ⚠️ Настроить `NEXT_PUBLIC_API_URL` от backend URL

### Claude-mem:
- [ ] 📝 Установить через `/plugin install claude-mem`
- [ ] 📝 Перезапустить Claude Code
- [ ] 📝 Проверить работу на http://localhost:37777

---

## 🎯 9. Рекомендуемая последовательность

### Сессия 1: Исправить Frontend (15 мин)
```bash
cd /home/user/oneiro-scope

# 1. Удалить дубликат layout
rm frontend/app/layout.tsx

# 2. Установить зависимости
cd frontend
npm ci

# 3. Проверить сборку
npm run build

# 4. Если успех - коммит
git add .
git commit -m "fix: remove duplicate root layout causing Server Components error"
git push
```

### Сессия 2: Очистить структуру (10 мин)
```bash
# Решить что делать с landing
# Вариант B - удалить:
rm index.html
rm -rf styles/

# Очистить Python файлы
mv tests/*.py backend/tests/
rmdir tests
rm swisseph.py timezonefinder.py
rm -rf geopy/ pandas/ oneiro-scope/

# Коммит
git add .
git commit -m "refactor: cleanup project structure, remove generated files from root"
git push
```

### Сессия 3: Исправить Backend и Render (20 мин)
- Обновить backend тесты
- Настроить переменные Render
- Деплой и проверка

---

## 📞 10. Выводы

### ✅ Что работает:
- Backend структура правильная
- Astrology geocoder исправлен (PR #39)
- Git история в порядке
- Документация актуальна

### ❌ Что сломано:
- **Frontend не может собраться** (нет node_modules)
- **Server Components error** (дубликат layout)
- **Структура проекта загрязнена** (landing + Python файлы в корне)
- **Claude-mem не установлен**

### ⚠️ Что требует внимания:
- Backend тесты (устаревшие импорты)
- Render environment variables
- ENVIRONMENT=production на деплое

---

## 🚀 Следующий шаг

**НЕМЕДЛЕННО:** Исправить frontend layout и установить зависимости.

```bash
# Выполнить сейчас:
rm /home/user/oneiro-scope/frontend/app/layout.tsx
cd /home/user/oneiro-scope/frontend && npm ci
```

Это разблокирует сборку frontend и устранит Server Components error.

---

**Prepared by:** Claude (Sonnet 4.5)
**Investigation time:** 2025-12-17
**Status:** ✅ Completed
**Next:** Awaiting user decision on actions

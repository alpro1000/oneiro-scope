# План очистки структуры проекта OneiroScope

## Дата: 2025-12-16

## Проблема

Codex сгенерировал landing page и другие файлы не в папке `frontend/`, а в корневой папке проекта. Это нарушает архитектуру проекта и создает путаницу.

## Найденные файлы, которые не должны быть в корневой папке:

### 1. Landing Page файлы (сгенерированы Codex)
- `index.html` - HTML landing page OneiroScope
- `styles/` - CSS стили
  - `styles/site.css` - основные стили
  - `styles/tokens.css` - дизайн-токены

### 2. Python файлы (должны быть в backend или удалены)
- `swisseph.py` - Swiss Ephemeris модуль
- `timezonefinder.py` - TimeZone finder модуль
- `geopy/` - Geocoding библиотека
- `pandas/` - Pandas библиотека

### 3. Тесты (должны быть в backend/tests)
- `tests/conftest.py`
- `tests/test_integration_dreamy_swisseph.py`

### 4. Пустые папки
- `oneiro-scope/` - пустая папка (нужно удалить)

---

## Правильная структура проекта

Согласно `CLAUDE.md` и `README.md`, проект должен иметь следующую структуру:

```
oneiro-scope/
├── backend/              # FastAPI backend
│   ├── app/
│   ├── api/
│   ├── services/
│   ├── core/
│   ├── models/
│   ├── data/
│   └── tests/           # ← Сюда тесты
├── frontend/            # Next.js frontend
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── messages/
│   ├── styles/          # ← Сюда styles (frontend имеет свою папку styles)
│   └── public/          # ← Сюда статические файлы (index.html может быть лендингом)
├── docs/
├── data/
├── scripts/
├── docker-compose.yml
├── render.yaml
└── README.md
```

---

## План действий

### Шаг 1: Анализ landing page

**Вопросы для пользователя:**
1. Нужен ли вообще этот landing page (`index.html`)?
2. Если нужен, где его разместить:
   - **Вариант A**: В `frontend/public/` как статический landing
   - **Вариант B**: Создать отдельный Next.js route в `frontend/app/landing/`
   - **Вариант C**: Заменить текущую главную страницу `frontend/app/[locale]/page.tsx`

### Шаг 2: Переместить или удалить файлы

#### Вариант 1: Переместить landing в frontend (если нужен)

```bash
# Создать папку для статических файлов
mkdir -p frontend/public/landing

# Переместить HTML
mv index.html frontend/public/landing/

# Переместить стили
mv styles frontend/public/landing/

# Или интегрировать в Next.js:
# - index.html → конвертировать в React компонент
# - styles → импортировать в frontend/styles/
```

#### Вариант 2: Удалить landing (если не нужен)

```bash
# Удалить файлы landing page
rm index.html
rm -rf styles/
```

### Шаг 3: Переместить Python файлы

```bash
# Проверить, используются ли эти файлы
# Если это дубликаты библиотек - удалить
# Если это кастомные модули - переместить в backend

# Переместить тесты в backend
mv tests/conftest.py backend/tests/
mv tests/test_integration_dreamy_swisseph.py backend/tests/
rmdir tests

# Удалить дубликаты библиотек (они должны быть в venv)
rm swisseph.py
rm timezonefinder.py
rm -rf geopy/
rm -rf pandas/
```

### Шаг 4: Удалить пустые папки

```bash
# Удалить пустую папку
rmdir oneiro-scope/
```

### Шаг 5: Обновить .gitignore

Добавить в `.gitignore`:
```
# Python библиотеки не должны быть в корне
/swisseph.py
/timezonefinder.py
/geopy/
/pandas/

# Landing page files (если решено удалить)
/index.html
/styles/
```

---

## Рекомендации

### Для landing page:

**Рекомендую Вариант B**: Создать отдельный Next.js route

**Преимущества:**
- Единый фронтенд-стек (Next.js)
- Переиспользование компонентов
- Поддержка i18n (RU/EN)
- SSR/SSG для SEO
- Легкая интеграция с остальным приложением

**Шаги:**
1. Создать `frontend/app/[locale]/landing/page.tsx`
2. Конвертировать `index.html` в React компонент
3. Импортировать стили в `frontend/styles/landing.css`
4. Использовать существующие дизайн-токены из `frontend/styles/globals.css`

### Для Python файлов:

**Проверить зависимости:**
```bash
# В backend
cd backend
grep -r "import swisseph" .
grep -r "from swisseph" .
grep -r "import timezonefinder" .
```

Если эти файлы - дубликаты библиотек из `backend/requirements.txt`, их можно безопасно удалить.

---

## Следующие шаги

1. **Пользователь принимает решение** о landing page (оставить/удалить/переместить)
2. **Выполнить миграцию** файлов согласно выбранному варианту
3. **Проверить работу** приложения после изменений:
   ```bash
   # Backend
   cd backend && pytest

   # Frontend
   cd frontend && npm run build
   ```
4. **Закоммитить изменения**:
   ```bash
   git add .
   git commit -m "refactor: cleanup project structure - move landing to frontend, remove duplicate Python files"
   ```

---

## Чеклист

- [ ] Решение по landing page принято
- [ ] Landing page файлы перемещены/удалены
- [ ] Python файлы проверены и удалены/перемещены
- [ ] Тесты перемещены в `backend/tests/`
- [ ] Пустые папки удалены
- [ ] `.gitignore` обновлен
- [ ] Backend тесты проходят
- [ ] Frontend билдится без ошибок
- [ ] Изменения закоммичены

---

## Контакты

Если возникнут вопросы по структуре проекта, обратитесь к:
- `CLAUDE.md` - главный гайд по проекту
- `README.md` - документация
- `docs/REPO_AUDIT.md` - аудит репозитория

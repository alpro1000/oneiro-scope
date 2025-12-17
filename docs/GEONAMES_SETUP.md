# GeoNames API Setup Guide

## Регистрация аккаунта GeoNames (бесплатно!)

### Шаг 1: Регистрация

1. Откройте https://www.geonames.org/login
2. Нажмите **"create a new user account"**
3. Заполните форму:
   - Username: выберите уникальное имя (например: `oneiroscope_user`)
   - Email: ваш email
   - Password: придумайте пароль
4. Нажмите **"Create Account"**
5. Подтвердите email (проверьте почту)

### Шаг 2: Активация Free Web Services

**ВАЖНО:** По умолчанию Web Services отключены! Нужно активировать:

1. Войдите на https://www.geonames.org/login (используйте ваш username)
2. Нажмите на ваш username в правом верхнем углу
3. Выберите **"Manage Account"**
4. Найдите раздел **"Free Web Services"**
5. Поставьте галочку **"Enable"** или нажмите **"Click here to enable"**
6. Сохраните изменения

**Теперь у вас:**
- ✅ Username для API (запомните его!)
- ✅ 30,000 запросов в день (бесплатно)
- ✅ Доступ к geocoding API

---

## 💻 Локальная разработка (Development)

### Создание файла backend/.env

```bash
# Перейдите в папку backend
cd /home/user/oneiro-scope/backend

# Создайте .env файл (если его нет)
touch .env

# Откройте для редактирования
nano .env
```

### Добавьте в backend/.env:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/oneiroscope
DATABASE_URL_SYNC=postgresql://postgres:postgres@localhost:5432/oneiroscope

# Redis (опционально для локальной разработки)
REDIS_URL=redis://localhost:6379/0

# GeoNames API (ВАЖНО!)
GEONAMES_USERNAME=ваш_username_с_geonames
GEONAMES_LANG=ru

# LLM Keys (добавьте хотя бы один)
GROQ_API_KEY=gsk-...                 # FREE, рекомендуется для разработки
GEMINI_API_KEY=...                   # или Gemini
OPENAI_API_KEY=sk-...                # или OpenAI
ANTHROPIC_API_KEY=sk-ant-...         # или Anthropic

# Секретный ключ (для JWT)
SECRET_KEY=your-super-secret-key-change-in-production
ALGORITHM=HS256

# Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# CORS (frontend URL)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

**Замените:**
- `ваш_username_с_geonames` → ваш реальный username с GeoNames
- `gsk-...` → ваш API ключ от Groq/OpenAI/Anthropic (хотя бы один)

**Сохраните файл:**
- В nano: `Ctrl+O`, `Enter`, `Ctrl+X`
- В vim: `Esc`, `:wq`, `Enter`

---

## 🚀 Production на Render.com

### Где добавить переменные окружения на Render:

1. **Откройте Render Dashboard:**
   - Перейдите на https://dashboard.render.com
   - Найдите ваш backend service (oneiro-scope-backend)

2. **Откройте настройки сервиса:**
   - Нажмите на ваш backend service
   - Перейдите во вкладку **"Environment"**

3. **Добавьте переменные окружения:**

   Нажмите **"Add Environment Variable"** и добавьте:

   | Key | Value | Notes |
   |-----|-------|-------|
   | `GEONAMES_USERNAME` | `ваш_username` | Username с GeoNames.org |
   | `GEONAMES_LANG` | `ru` | Язык для ответов (русский) |
   | `ENVIRONMENT` | `production` | **ВАЖНО!** Иначе `init_db()` запустится в проде |
   | `SECRET_KEY` | `сгенерируйте_случайную_строку` | Для JWT токенов |
   | `ALLOWED_ORIGINS` | `https://ваш-frontend.onrender.com` | URL вашего фронтенда |
   | `DATABASE_URL` | `автоматически_от_Render` | Уже должно быть |
   | `REDIS_URL` | `автоматически_от_Render` | Если Redis добавлен |

4. **Сохраните изменения:**
   - Нажмите **"Save Changes"**
   - Render автоматически **перезапустит** backend с новыми переменными

5. **Очистите кеш сборки (если фронтенд):**
   - Перейдите в frontend service
   - Нажмите **"Manual Deploy"**
   - Выберите **"Clear build cache & Deploy"**
   - Это нужно чтобы `NEXT_PUBLIC_*` переменные обновились

---

## ✅ Проверка правильности настройки

### Локально:

```bash
# Проверьте, что .env файл создан
cat backend/.env | grep GEONAMES

# Должно показать:
# GEONAMES_USERNAME=ваш_username
# GEONAMES_LANG=ru
```

### На Render:

1. Откройте ваш backend service на Render
2. Перейдите во вкладку **"Logs"**
3. После деплоя проверьте логи на наличие ошибок
4. При старте НЕ должно быть сообщений о `GEONAMES_USERNAME not set`

---

## 🧪 Тестирование

### Локальный тест:

```bash
# Запустите Python в backend venv
cd /home/user/oneiro-scope
backend/.venv/bin/python

# Тест GeoNames lookup:
>>> import asyncio
>>> import sys
>>> sys.path.insert(0, '.')
>>> from backend.utils.geonames_resolver import geonames_lookup
>>>
>>> async def test():
...     result = await geonames_lookup("Москва")
...     print(f"✅ Resolved: {result['resolved_name']}, {result['country']}")
...
>>> asyncio.run(test())

# Должно показать:
# ✅ Resolved: Moscow, Russia
```

### API тест:

```bash
# Запустите backend
cd /home/user/oneiro-scope
uvicorn backend.app.main:app --reload --port 8000

# В другом терминале:
curl -X POST http://localhost:8000/api/v1/astrology/natal-chart \
  -H "Content-Type: application/json" \
  -d '{
    "birth_date": "1990-01-01",
    "birth_time": "12:00",
    "birth_place": "Москва"
  }'

# Должно вернуть 201 + natal chart JSON (не 500!)
```

---

## 🔒 Безопасность

**НИКОГДА не коммитьте:**
- `backend/.env` (уже в .gitignore)
- API ключи в коде
- Пароли в открытом виде

**Проверьте .gitignore:**
```bash
cat .gitignore | grep .env

# Должно быть:
# .env
# *.env
# .env.local
```

---

## ❓ Troubleshooting

### "Place not found" для русских названий:

**Проблема:** GeoNames не находит "Москва"
**Решение:** Проверьте что `GEONAMES_LANG=ru` установлена. Если не помогает, наш resolver автоматически попробует транслитерацию (Moskva).

### "GeoNames API limit exceeded"

**Проблема:** 30,000 запросов в день исчерпаны
**Решение:**
1. Проверьте кеширование работает (LRU cache на 512 записей)
2. Используйте разные username для dev/prod
3. Рассмотрите платный план GeoNames Premium

### "demo user disabled"

**Проблема:** Используется demo username (ограничен 20,000 запросов/час на ВСЕХ пользователей)
**Решение:** Зарегистрируйте свой бесплатный аккаунт!

---

## 📊 Квоты GeoNames

| Plan | Requests/day | Requests/hour | Cost |
|------|-------------|---------------|------|
| **Free** | 30,000 | 2,000 | $0 |
| Premium | 200,000 | No limit | $250/year |
| Enterprise | Custom | No limit | Custom |

Для oneiro-scope Free плана более чем достаточно благодаря кешированию!

---

**Готово!** Теперь ваш сервис может геокодировать русские и латинские названия городов через GeoNames API.

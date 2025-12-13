# Деплой OneiroScope на Render (blueprint `render.yaml`)

Пошаговая инструкция для публикации фронтенда (Next.js) и бэкенда (FastAPI) на Render через готовый blueprint. Blueprint поднимает Postgres, Redis, backend и frontend, связывает их переменными окружения и адресами сервисов.

## 1) Предварительные требования
- Аккаунт Render с доступом к GitHub.
- Репозиторий с вашими изменениями в GitHub.
- Готовые ключи LLM (минимум Groq для dev, Gemini для prod). Опционально: Together, OpenAI, Anthropic.

## 2) Проверить проект локально
```bash
# Frontend
cd frontend
npm ci
npm run build && npm run start

# Backend
cd ../backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app.main:app --reload
```
Убедитесь, что http://localhost:3000 и http://localhost:8000/docs работают, а фронтенд успешно обращается к `/api/v1/*`.

## 3) Заполнить переменные окружения
Blueprint создаёт большинство значений автоматически, но ключи LLM и секреты нужно добавить вручную в Render → Settings → Environment.

| Ключ | Где использовать | Назначение |
| --- | --- | --- |
| `SECRET_KEY` | Backend | JWT/crypto секрет (сгенерируйте сами) |
| `GROQ_API_KEY` | Backend, Frontend | Дешёвый dev-провайдер (рекомендуется) |
| `GEMINI_API_KEY` | Backend, Frontend | Продакшен-провайдер (дешевле всего) |
| `TOGETHER_API_KEY` | Backend | Доп. fallback |
| `OPENAI_API_KEY` | Backend | Доп. fallback |
| `ANTHROPIC_API_KEY` | Backend | Доп. fallback |
| `ALLOWED_ORIGINS` | Backend | URL фронтенда (Render выдаст после создания) |

Blueprint автоматически подставит:
- `DATABASE_URL` / `DATABASE_URL_SYNC` из Postgres.
- `REDIS_URL` из Redis.
- `LUNAR_API_URL` и `NEXT_PUBLIC_LUNAR_API_URL` — маршруты backend для SSR/CSR.
- `NODE_ENV=production`, `LUNAR_DEFAULT_TZ=UTC`.

## 4) Создать ресурсы по blueprint
1. В Render нажмите **New + → Blueprint**.
2. Укажите Git-репозиторий и ветку.
3. В превью убедитесь, что будут созданы:
   - Postgres (`oneiroscope-postgres`)
   - Redis (`oneiroscope-redis`)
   - Web Service (Python) — backend (`oneiroscope-backend`)
   - Web Service (Node) — frontend (`oneiroscope-frontend`)
4. Нажмите **Apply**. Render свяжет сервисы между собой (URLs и строки подключения уйдут в переменные окружения).

## 5) Первые деплой и миграции
- Запустите **Manual Deploy → Deploy latest commit** для backend и frontend.
- Если у вас есть миграции Alembic, добавьте команду запуска в Render (или выполните из консоли):
  ```bash
  alembic upgrade head
  ```

## 6) Смоук-тест продакшена
- Откройте URL фронтенда из Render и проверьте:
  - Страница календаря рендерится, кнопка «Today» работает.
  - Разделы астрологии и снов запрашивают `/api/v1/astrology/*` и `/api/v1/dreams/*` без ошибок.
- Проверьте http(s)://<backend-url>/health — должно вернуть `{ "status": "ok" }`.
- Убедитесь, что нет ошибок в браузерной консоли и логах Render.

## 7) Дальнейшие действия
- Добавьте Swiss Ephemeris (`pyswisseph`) для точной астрономии, если планируете продакшн-тарифы.
- Настройте домен/HTTPS в Render, если требуется публичный доступ.
- Включите авто-деплой при пушах в основную ветку.

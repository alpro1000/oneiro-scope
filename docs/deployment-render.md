# Deploying OneiroScope (frontend + backend) to Render

This guide covers publishing both the Next.js frontend (`frontend/`) and the FastAPI backend (`backend/`) on Render using the
provided `render.yaml` blueprint. The blueprint provisions Postgres, Redis, the backend API, and the frontend web service in
one click.

## Prerequisites
- Render account with GitHub access.
- Repository pushed to GitHub.
- `OPENAI_API_KEY` available (used by the chat assistant).

## 1. Prepare the repository locally
1. Copy `frontend/.env.example` to `.env.local` for local testing.
2. Install dependencies and verify the production build locally:
   ```bash
   cd frontend
   npm ci
   npm run build
   npm run start
   ```
   > `npm ci` may require the Playwright binary. In CI, prefer using `npm ci --omit=dev` if you do not run tests.
3. (Optional) Validate the backend starts locally:
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn backend.app.main:app --reload
   ```

## 2. Create resources from the blueprint
1. In Render click **New + → Blueprint**.
2. Point to this repository and select the branch with your changes.
3. Confirm the `render.yaml` preview shows:
   - **Postgres** database (`oneiroscope-postgres`).
   - **Redis** instance (`oneiroscope-redis`).
   - **Web Service (Python)** for the backend (`oneiroscope-backend`).
   - **Web Service (Node)** for the frontend (`oneiroscope-frontend`).
4. Click **Apply** to create all resources. Render will automatically wire environment variables (database/Redis URLs and
   service URLs) according to the blueprint.

## 3. Configure environment variables
The blueprint sets up most variables automatically. Manually add the following:

| Key | Value | Applied to |
| --- | ----- | ---------- |
| `OPENAI_API_KEY` | `<your key>` | Backend and frontend |
| `SECRET_KEY` | *(auto-generated, replace if rotating)* | Backend |
| `ALLOWED_ORIGINS` | *(optional override; defaults to frontend URL from blueprint)* | Backend |

Other variables are provided automatically:
- `DATABASE_URL`, `DATABASE_URL_SYNC` from Postgres.
- `REDIS_URL` from Redis.
- `LUNAR_API_URL` and `NEXT_PUBLIC_LUNAR_API_URL` point to the backend `/api/v1/lunar` endpoint for server and client fetches.
- `NODE_ENV` and `LUNAR_DEFAULT_TZ` default to `production` and `UTC` respectively.

## 4. Trigger the first deploy
- For each service, click **Manual Deploy → Deploy latest commit**.
- Wait for the backend build to finish (`pip install -r requirements.txt` then `uvicorn ...`).
- Wait for the frontend build to finish (`npm install && npm run build` then `npm start`).

## 5. Smoke test the deployment
1. Open the frontend Render URL.
2. Verify that the `LunarWidget` renders, the **Today** button jumps to the current date, and the month accordion expands.
3. Open the browser network tab and confirm `/api/v1/lunar?date=YYYY-MM-DD&locale=ru&tz=UTC` requests succeed (mock payload is
   returned until the lunar service is implemented).
4. Hit the backend health check directly: `<backend-url>/health` should return `{"status": "ok"}`.
5. Confirm there are no console errors.

## 6. Keep CI green
- CI pipelines should continue using `npm ci` (defined in the repo). No deployment-specific changes are required beyond the new
  environment variables.

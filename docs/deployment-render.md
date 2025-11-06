# Deploying the LunarWidget frontend to Render

This guide walks through deploying the Next.js frontend (`frontend/`) to Render using the mock `/api/lunar` route.

## Prerequisites
- Render account with GitHub access.
- Repository pushed to GitHub.
- `OPENAI_API_KEY` available (used by the chat assistant).

## 1. Prepare the repository
1. Copy `frontend/.env.example` to `.env.local` for local testing.
2. Install dependencies and verify the production build locally:
   ```bash
   cd frontend
   npm ci
   npm run build
   npm run start
   ```
   > `npm ci` may require the Playwright binary. In CI, prefer using `npm ci --omit=dev` if you do not run tests.

## 2. Create the Render service
1. In Render click **New + → Web Service**.
2. Select the GitHub repository and branch.
3. Set **Root Directory** to `frontend`.
4. Build Command: `npm install && npm run build`.
5. Start Command: `npm run start`.
6. Choose the **Free** plan for previews or another plan as needed.

## 3. Configure environment variables
Add the following variables in Render → **Environment**:

| Key | Value |
| --- | ----- |
| `NODE_ENV` | `production` |
| `OPENAI_API_KEY` | `<your key>` |
| `LUNAR_API_URL` | *(leave empty to use mock API or point to backend URL)* |
| `NEXT_PUBLIC_LUNAR_API_URL` | `/api/lunar` |
| `LUNAR_DEFAULT_TZ` | `UTC` |

## 4. Trigger the first deploy
- Click **Manual Deploy → Deploy latest commit**.
- Wait for the build to finish. Render installs dependencies, runs `npm run build`, and then starts the Next.js server.

## 5. Smoke test the deployment
1. Open the Render URL.
2. Verify that the `LunarWidget` renders, the **Today** button jumps to the current date, and the month accordion expands.
3. Check the browser network tab that calls to `/api/lunar` succeed (mock data is returned if the backend is unavailable).
4. Confirm there are no console errors.

## 6. Keep CI green
- CI pipelines should continue using `npm ci` (defined in the repo). No deployment-specific changes are required beyond the new environment variables.

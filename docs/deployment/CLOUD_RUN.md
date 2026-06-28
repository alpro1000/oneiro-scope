# OneiroScope on Google Cloud Run + Vertex AI

Deploying OneiroScope to **Cloud Run** with **Vertex AI (formerly
Google Vertex)** as the primary LLM. This is the preferred path for
owners who already use GCP.

## Why Cloud Run + Vertex AI

| | Cloud Run | Render |
|---|---|---|
| **Cold start** | ~1-2s for Python | ~5-10s on free tier |
| **Auto-scale to zero** | yes (no idle cost) | only on paid tier |
| **Pricing** | per-request (cheap until traffic) | flat monthly |
| **Vertex AI integration** | native via metadata-server ADC | needs explicit token |
| **EU data residency** | yes (region `europe-west1` etc.) | US/EU available |

For a solo-founder workload (mostly idle, occasional bursts), Cloud
Run is significantly cheaper than Render at ~$0-15/month for
typical traffic.

## Architecture overview

```
┌──────────────────────────────────────────────────────────┐
│  Cloud Run Service (backend FastAPI + MCP server)        │
│  - Region: europe-west1                                  │
│  - Min instances: 0  (scale to zero)                     │
│  - Max instances: 10                                     │
│  - Service account with roles/aiplatform.user            │
└──────────────┬───────────────────────────────────────────┘
               │ ADC via metadata-server (no token needed)
               ▼
┌──────────────────────────────────────────────────────────┐
│  Vertex AI (Gemini 1.5 Flash / Gemini 1.5 Pro)           │
│  - Region: europe-west1                                  │
│  - $0.075 / 1M tokens (Flash) — primary                  │
│  - Auto-detected by backend/core/llm_provider.py         │
└──────────────────────────────────────────────────────────┘
               │
┌──────────────────────────────────────────────────────────┐
│  Cloud SQL (Postgres 15)                                 │
│  - Region: europe-west1                                  │
│  - 1 vCPU, 614 MB, ~$8/mo                                │
│  - Connected via Cloud SQL Auth Proxy                    │
└──────────────────────────────────────────────────────────┘

Optional:
  - Cloud Memorystore (Redis) for cost-tracker + sessions
  - Cloud Storage bucket for static assets / Swiss Ephemeris files
```

## Step 1 — Project setup

```bash
# Create or pick a project
gcloud projects create oneiroscope-prod
gcloud config set project oneiroscope-prod

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  aiplatform.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com
```

## Step 2 — Service account for Cloud Run

Cloud Run runs your code AS a service account. That service account
needs permissions to call Vertex AI and read Secret Manager.

```bash
SA_NAME=oneiroscope-runtime
gcloud iam service-accounts create $SA_NAME \
  --display-name="OneiroScope runtime"

SA_EMAIL="${SA_NAME}@oneiroscope-prod.iam.gserviceaccount.com"

# Permission to call Vertex AI
gcloud projects add-iam-policy-binding oneiroscope-prod \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/aiplatform.user"

# Permission to read Secret Manager
gcloud projects add-iam-policy-binding oneiroscope-prod \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"

# Permission to talk to Cloud SQL
gcloud projects add-iam-policy-binding oneiroscope-prod \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/cloudsql.client"
```

## Step 3 — Secrets in Secret Manager

DO NOT put secrets in env vars or in the image. Use Secret Manager.

```bash
# Create secrets
echo -n "$(openssl rand -hex 32)" | gcloud secrets create secret-key \
  --data-file=- --replication-policy="user-managed" --locations=europe-west1

echo -n "$LEMON_API_KEY" | gcloud secrets create lemon-api-key --data-file=- --locations=europe-west1
echo -n "$LEMON_WEBHOOK_SECRET" | gcloud secrets create lemon-webhook-secret --data-file=- --locations=europe-west1
echo -n "$RESEND_API_KEY" | gcloud secrets create resend-api-key --data-file=- --locations=europe-west1

# Database URL (after Step 4)
echo -n "$DATABASE_URL" | gcloud secrets create database-url --data-file=- --locations=europe-west1
```

## Step 4 — Cloud SQL Postgres

```bash
gcloud sql instances create oneiroscope-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=europe-west1 \
  --storage-size=10GB \
  --storage-auto-increase \
  --backup-start-time=02:00

gcloud sql databases create oneiroscope --instance=oneiroscope-db
gcloud sql users create oneiroscope --instance=oneiroscope-db --password="<random>"
```

Get the connection name (`<PROJECT>:<REGION>:<INSTANCE>`):

```bash
gcloud sql instances describe oneiroscope-db --format='value(connectionName)'
# e.g. oneiroscope-prod:europe-west1:oneiroscope-db
```

Connection string for Cloud Run via Cloud SQL Auth Proxy:

```
postgresql+asyncpg://oneiroscope:<pwd>@/oneiroscope?host=/cloudsql/oneiroscope-prod:europe-west1:oneiroscope-db
```

## Step 5 — Build & push the container

OneiroScope ships with `backend/Dockerfile` (multi-stage Python 3.11).
Build via Cloud Build for the right architecture (linux/amd64):

```bash
# Create Artifact Registry repo
gcloud artifacts repositories create oneiroscope \
  --repository-format=docker --location=europe-west1

# Build and push
gcloud builds submit . \
  --tag europe-west1-docker.pkg.dev/oneiroscope-prod/oneiroscope/backend:latest \
  --timeout=15m
```

## Step 6 — Deploy to Cloud Run

```bash
gcloud run deploy oneiroscope-backend \
  --image=europe-west1-docker.pkg.dev/oneiroscope-prod/oneiroscope/backend:latest \
  --region=europe-west1 \
  --service-account=$SA_EMAIL \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=10 \
  --port=8000 \
  --allow-unauthenticated \
  --add-cloudsql-instances=oneiroscope-prod:europe-west1:oneiroscope-db \
  --set-env-vars="ENVIRONMENT=production,VERTEX_PROJECT=oneiroscope-prod,VERTEX_LOCATION=europe-west1,VERTEX_MODEL_ID=gemini-1.5-flash-002,LUNAR_DEFAULT_TZ=Europe/Berlin,ALLOWED_ORIGINS=https://oneiroscope.app" \
  --set-secrets="SECRET_KEY=secret-key:latest,DATABASE_URL=database-url:latest,LEMON_API_KEY=lemon-api-key:latest,LEMON_WEBHOOK_SECRET=lemon-webhook-secret:latest,RESEND_API_KEY=resend-api-key:latest"
```

## Step 7 — Verify Vertex AI auto-detection

OneiroScope's `_provider_configured(LLMProvider.VERTEX)` checks
`K_SERVICE` (set automatically by Cloud Run) AND `VERTEX_PROJECT`. If
both present, Vertex is activated and `google.auth.default()` mints
the access token from the runtime service account — **no explicit
token in env**.

Test:

```bash
SERVICE_URL=$(gcloud run services describe oneiroscope-backend \
  --region=europe-west1 --format='value(status.url)')

curl "$SERVICE_URL/health"
# {"status":"healthy", "ephemeris":{"engine":"MOSEPH",...}}

# Check Vertex is in the LLM provider list
curl "$SERVICE_URL/health/detailed"
```

Cloud Run logs (`gcloud run services logs read oneiroscope-backend`)
should show:

```
LLM providers available: vertex, groq, gemini, ...
Ephemeris: MOSEPH (analytic fallback)
```

## Step 8 — Optional: Swiss Ephemeris binary files

For arc-second precision instead of MOSEPH analytic:

```bash
# Create Cloud Storage bucket
gsutil mb -l europe-west1 gs://oneiroscope-ephe

# Upload .se1 files (download from astro.com or compile from source)
gsutil -m cp ephe/*.se1 gs://oneiroscope-ephe/

# Mount via Cloud Run volume (requires gen2 execution environment)
gcloud run services update oneiroscope-backend \
  --region=europe-west1 \
  --execution-environment=gen2 \
  --add-volume="name=ephe,type=cloud-storage,bucket=oneiroscope-ephe" \
  --add-volume-mount="volume=ephe,mount-path=/var/ephe" \
  --update-env-vars="SE_EPHE_PATH=/var/ephe"
```

After this, `/health` will show `engine: SWIEPH` instead of MOSEPH.

## Step 9 — Custom domain

```bash
gcloud beta run domain-mappings create \
  --service=oneiroscope-backend \
  --domain=api.oneiroscope.app \
  --region=europe-west1
```

Then add the CNAME record GCP gives you to your DNS provider.

## Step 10 — Frontend on Cloud Run (optional)

If you also want the Next.js frontend on Cloud Run:

```bash
cd frontend
gcloud builds submit . \
  --tag europe-west1-docker.pkg.dev/oneiroscope-prod/oneiroscope/frontend:latest

gcloud run deploy oneiroscope-frontend \
  --image=europe-west1-docker.pkg.dev/oneiroscope-prod/oneiroscope/frontend:latest \
  --region=europe-west1 \
  --memory=512Mi \
  --min-instances=0 --max-instances=10 \
  --port=3000 \
  --allow-unauthenticated \
  --set-env-vars="NEXT_PUBLIC_API_URL=https://api.oneiroscope.app"
```

## Cost estimate (steady-state, MVP traffic ≤ 1k MAU)

| Item | Cost/month |
|---|---|
| Cloud Run backend (scale-to-zero, ~10M req-seconds) | $0-5 |
| Cloud Run frontend (same) | $0-5 |
| Cloud SQL db-f1-micro | $7-9 |
| Cloud Storage (ephemeris ~50 MB) | ~$0 |
| Secret Manager (5 secrets, 10k ops) | ~$0.50 |
| Vertex AI (Gemini Flash, ~5M tokens/mo) | ~$0.40 |
| Egress to internet | ~$1 |
| **Total** | **≈ $10-21/mo** |

Compare to Render's flat $14-21/mo for backend+db.

Cloud Run wins when traffic is bursty (most MVPs); Render wins when
traffic is constant (cold starts irrelevant). Given the user's
expected pattern (premium Strategic Analyst consultations, not high
frequency), **Cloud Run is the right pick**.

## Common pitfalls

- **Forgetting `K_SERVICE` detection** — the `_provider_configured`
  check needs `VERTEX_PROJECT` set explicitly even on Cloud Run.
  Without it, Vertex won't show up in the provider list.
- **MOSEPH vs SWIEPH** — Chiron + asteroids fail under MOSEPH. If
  Strategic Analyst calls `compute_transits` with Chiron, expect an
  error message. Either drop Chiron from the body list (already
  done in `transits_engine.py`) or upload `seas_18.se1` to Step 8's
  bucket.
- **Cold start with Swiss Ephemeris** — `pyswisseph` loads its data
  on first import (~200 ms). Add a startup probe that imports it,
  so the first user request doesn't pay this cost.
- **Cloud SQL connection pooling** — `asyncpg` pools have to be
  configured carefully for serverless. Use `pool_size=5,
  max_overflow=2` and idle timeout < Cloud Run's instance lifetime.
- **No background tasks** — Cloud Run doesn't run anything when no
  request is in flight. For cron-like jobs (cost-tracker cleanup,
  pending-deletion purge), use Cloud Scheduler → Cloud Run jobs or
  Cloud Tasks → endpoint.
- **Lemon Squeezy webhook IP allowlist** — Cloud Run accepts from
  anywhere by default. Apply Cloud Armor if you want IP filtering.

## CI/CD via Cloud Build trigger

```bash
# Connect GitHub repo
gcloud builds triggers create github \
  --repo-name=oneiro-scope --repo-owner=alpro1000 \
  --branch-pattern="^main$" \
  --build-config=cloudbuild.yaml
```

`cloudbuild.yaml` (add to repo root):

```yaml
steps:
  - name: gcr.io/cloud-builders/docker
    args:
      - build
      - --tag=europe-west1-docker.pkg.dev/$PROJECT_ID/oneiroscope/backend:$COMMIT_SHA
      - --tag=europe-west1-docker.pkg.dev/$PROJECT_ID/oneiroscope/backend:latest
      - .
  - name: gcr.io/cloud-builders/docker
    args: [push, --all-tags, europe-west1-docker.pkg.dev/$PROJECT_ID/oneiroscope/backend]
  - name: gcr.io/google.com/cloudsdktool/cloud-sdk
    entrypoint: gcloud
    args:
      - run
      - deploy
      - oneiroscope-backend
      - --image=europe-west1-docker.pkg.dev/$PROJECT_ID/oneiroscope/backend:$COMMIT_SHA
      - --region=europe-west1
images:
  - europe-west1-docker.pkg.dev/$PROJECT_ID/oneiroscope/backend
```

Every push to `main` builds and deploys automatically.

# Octavia – Final, Hyper-Detailed Repository Structure

```
octavia/
├── .github/
│   └── workflows/
│       ├── ci.yml                     # Lint + type check + tests
│       └── deploy.yml                 # Terraform + RunPod fleet on push to main
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI entrypoint
│   │   ├── celery_app.py              # Celery = make_celery(app)
│   │   ├── config.py                  # Pydantic Settings (env vars)
│   │   ├── database/
│   │   │   ├── base.py
│   │   │   ├── session.py
│   │   │   └── models/                      # SQLAlchemy models
│   │   ├── schemas/
│   │   │   ├── user.py
│   │   │   ├── job.py
│   │   │   └── voice.py
│   │   ├── routers/
│   │   │   ├── auth.py                # Clerk webhook + JWT verification
│   │   │   ├── uploads.py             # Pre-signed BunnyCDN URLs
│   │   │   ├── jobs.py                # CRUD + SSE endpoint
│   │   │   ├── voices.py              # My Voices + cloning status
│   │   │   └── webhooks.py            # BunnyCDN + Stripe + RunPod callbacks
│   │   ├── workers/
│   │   │   ├── __init__.py
│   │   │   ├── magic_pipeline.py      # The full 10-step Magic Mode (your holy grail)
│   │   │   ├── diarization.py         # pyannote + clustering
│   │   │   ├── cloning.py             # on-the-fly XTTS + RVC
│   │   │   ├── ducking.py             # sidechaincompress filter generator
│   │   │   └── sync.py                # atempo + pause insertion engine
│   │   ├── utils/
│   │   │   ├── bunnycdn.py            # Signed URLs + webhook verification
│   │   │   ├── ffmpeg.py              # All filter chains as Python functions
│   │   │   └── security.py            # Per-job AES-256 encryption keys
│   │   └── dependencies.py            # JWT, DB session, rate limiting
│   │
│   ├── scripts/
│   │   ├── run_worker.sh              # Entry point for RunPod pods
│   │   └── healthcheck.py
│   │
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/
│   │
│   ├── alembic/                       # Database migrations
│   ├── Dockerfile                     # Multi-stage with torch + ffmpeg static
│   ├── requirements.txt
│   └── pyproject.toml
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx                   # Dashboard
│   │   ├── upload/
│   │   │   └── page.tsx
│   │   ├── jobs/
│   │   │   ├── page.tsx
│   │   │   └── [id]/
│   │   │       └── page.tsx           # Live progress + sample chunks
│   │   ├── voices/
│   │   │   └── page.tsx               # My Voices + cloning UI
│   │   └── settings/
│   │       └── page.tsx               # Magic Mode toggles (exact purple design)
│   │
│   ├── components/
│   │   ├── ui/                        # shadcn components (extended with our purple theme)
│   │   ├── ProgressSSE.tsx
│   │   ├── SampleChunkPlayer.tsx
│   │   └── MagicToggleGroup.tsx
│   │
│   ├── lib/
│   │   ├── api.ts                     # TanStack Query wrappers
│   │   └── clerk.ts
│   │
│   ├── public/
│   │   └── favicon.ico
│   │
│   ├── Dockerfile
│   ├── next.config.js
│   ├── tailwind.config.ts
│   └── package.json
│
├── terraform/
│   ├── modules/
│   │   ├── runpod_fleet/
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   └── bunnycdn/
│   │       ├── main.tf
│   │       └── variables.tf
│   │
│   ├── environments/
│   │   ├── prod.tfvars
│   │   └── staging.tfvars
│   │
│   ├── main.tf
│   ├── providers.tf
│   ├── variables.tf
│   └── backend.tf                     # S3 backend on Backblaze B2
│
├── docker-compose.yml                 # Local dev + Swarm/K8s ready
├── docker-compose.prod.yml            # Production override (GPU + volumes)
├── .env.example
├── .gitignore
├── README.md
└── Makefile                           # make dev / make prod / make gpu-test

```

## Exact File Tree (copy-paste ready)

```
octavia/
├── .github/workflows/ci.yml
├── .github/workflows/deploy.yml
├── backend/app/main.py
├── backend/app/celery_app.py
├── backend/app/config.py
├── backend/app/database/__init__.py
├── backend/app/database/session.py
├── backend/app/database/models/job.py
├── backend/app/database/models/user.py
├── backend/app/database/models/voice.py
├── backend/app/routers/auth.py
├── backend/app/routers/uploads.py
├── backend/app/routers/jobs.py
├── backend/app/routers/voices.py
├── backend/app/routers/webhooks.py
├── backend/app/workers/magic_pipeline.py
├── backend/app/workers/diarization.py
├── backend/app/workers/cloning.py
├── backend/app/workers/ducking.py
├── backend/app/workers/sync.py
├── backend/app/utils/bunnycdn.py
├── backend/app/utils/ffmpeg.py
├── backend/Dockerfile
├── backend/requirements.txt
├── frontend/app/page.tsx
├── frontend/app/upload/page.tsx
├── frontend/app/jobs/page.tsx
├── frontend/app/jobs/[id]/page.tsx
├── frontend/app/voices/page.tsx
├── frontend/app/settings/page.tsx
├── frontend/components/MagicToggleGroup.tsx
├── frontend/Dockerfile
├── terraform/main.tf
├── terraform/modules/runpod_fleet/main.tf
├── docker-compose.yml
└── Makefile

```

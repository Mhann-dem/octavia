# Octavia — Data model (Postgres examples)

This document includes recommended data structures for the Octavia backend. The examples are PostgreSQL-friendly and oriented towards the job-driven architecture described in `documentation/architecture.md`.

## Core tables

### users

Stores application users and account information.

Columns:

- id (uuid) — primary key
- email (text) — unique
- password_hash (text) — hashed password (bcrypt/argon2)
- is_verified (boolean) — whether email was verified
- credits (bigint) — user's current credit balance (use integer credits)
- role (text) — user role: 'user' | 'admin' | 'team'
- created_at, updated_at (timestamptz)

SQL example:

```sql
CREATE TABLE users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text UNIQUE NOT NULL,
  password_hash text NOT NULL,
  is_verified boolean DEFAULT FALSE,
  credits bigint DEFAULT 0,
  role text DEFAULT 'user',
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
```

### sessions

Tracks authenticated sessions or refresh tokens if using a server session store.

```sql
CREATE TABLE sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  user_agent text,
  ip_address text,
  created_at timestamptz DEFAULT now(),
  last_seen timestamptz
);
```

### projects

Organizes media and jobs per user project/translation context.

```sql
CREATE TABLE projects (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  name text,
  description text,
  created_at timestamptz DEFAULT now()
);
```

### media_files

Records reference to files in object storage.

Columns include: file id, project_id, user_id, path, media_type (video|audio), duration, size, mimetype, derived_from (nullable), metadata JSON.

```sql
CREATE TABLE media_files (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id uuid REFERENCES projects(id) ON DELETE CASCADE,
  user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  s3_key text NOT NULL,
  media_type text,
  duration_seconds numeric,
  size_bytes bigint,
  mimetype text,
  derived_from uuid NULL REFERENCES media_files(id),
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now()
);
```

### jobs

Central job table to track pipeline state (video_translation, audio_translation, subtitles etc.).

Columns: id, user_id, project_id, job_type, status, progress (0-100), input_media_id, output_media_id, metadata JSON, cost_credits, created_at, started_at, finished_at.

```sql
CREATE TYPE job_status AS ENUM ('pending','queued','running','failed','completed','cancelled');

CREATE TABLE jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  project_id uuid REFERENCES projects(id) ON DELETE SET NULL,
  job_type text NOT NULL,
  status job_status DEFAULT 'pending',
  progress int DEFAULT 0,
  input_media_id uuid REFERENCES media_files(id),
  output_media_id uuid NULL REFERENCES media_files(id),
  metadata jsonb DEFAULT '{}'::jsonb,
  cost_credits bigint DEFAULT 0,
  created_at timestamptz DEFAULT now(),
  started_at timestamptz NULL,
  finished_at timestamptz NULL
);
```

### job_segments

Optional table used to track finer-grained progress segments of a job (transcription chunks, TTS segments). Useful for resuming partial failures.

```sql
CREATE TABLE job_segments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id uuid REFERENCES jobs(id) ON DELETE CASCADE,
  segment_index int NOT NULL,
  start_ms int,
  end_ms int,
  status text DEFAULT 'pending',
  result jsonb,
  created_at timestamptz DEFAULT now(),
  finished_at timestamptz
);
```

### transactions

Records credit purchases and provider data (Polar.sh integrations).

```sql
CREATE TYPE tx_status AS ENUM ('pending','succeeded','failed','cancelled');

CREATE TABLE transactions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  provider text, -- 'polar'
  provider_payment_id text, -- provider unique id
  amount_cents bigint, -- currency minor units
  credits_bought bigint,
  status tx_status DEFAULT 'pending',
  webhook_payload jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz
);
```

### credits_history

Audit trail for credits changes (spend/additions).

```sql
CREATE TABLE credits_history (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid REFERENCES users(id) ON DELETE CASCADE,
  delta bigint, -- positive or negative
  reason text,
  job_id uuid REFERENCES jobs(id),
  created_at timestamptz DEFAULT now()
);
```

---

## Transactional notes

- Use SERIALIZABLE or at minimum REPEATABLE READ when deducting credits to avoid race conditions (check available credits, deduct, write credits_history in a single transaction). Database-level safeguards (row locking) recommended.

## Indexing & retention

- Index common lookup columns: jobs(user_id, status), media_files(user_id, project_id), transactions(user_id, provider_payment_id)
- Keep a retention policy for older artifacts or move them to cold storage (S3 Glacier etc.)

## Example read flow: get job status (API)

1. GET /api/jobs/:id -> query jobs by id + return progress + job metadata + presigned output url when completed

---

Next steps: implement migration files (Knex / Prisma / TypeORM) and wire the DB into the auth and job creation endpoints.

# Octavia — Backend Architecture

This document describes the recommended backend architecture for the Octavia web app (media translation, subtitling, dubbing and billing). It focuses on service boundaries, responsibilities, processing flows and integration points for the specific technology stack named in the requirements (OpenAI Whisper, Helsinki NLP, Coqui TTS, Polar.sh).

## Goals

- Reliable, scalable pipeline for media processing
- Clear separation of API and heavy worker jobs
- Fault tolerance, retries, and idempotency for long-running tasks
- Secure payments and credits management

## High-level components

1. API Server (HTTP, user-facing)

   - Responsibilities: auth, user management, project management, file / upload orchestration, job creation, billing endpoints, webhook handling
   - Technologies: Node.js + Fastify or Express, TypeScript, JWT/session cookies

2. Worker(s) (Background jobs)

   - Responsibilities: CPU/IO-heavy processing: audio extraction (ffmpeg), Whisper transcription, translation calls, TTS (Coqui), audio/video merge, subtitle formatting
   - Deployment: separate horizontally scalable worker instances (pool may be specialized: CPU workers, GPU workers if using on-prem Whisper)

3. Queue / Job Broker

   - Responsibilities: reliable job delivery, retries, delayed/restartable jobs, progress reporting
   - Technologies: Redis + BullMQ (Node) or RabbitMQ + worker framework; recommended: BullMQ with Redis for Node projects

4. Storage

   - Responsibilities: store uploaded files, intermediate artifacts, final outputs, public access via pre-signed URLs
   - Options: AWS S3 / DigitalOcean Spaces / Supabase / Azure Blob. For local dev use filesystem or MinIO

5. Database (Postgres recommended)

   - Responsibilities: user accounts, projects, jobs metadata, transactions, credits balances

6. External Integrations

   - OpenAI Whisper (hosted or self-hosted) — transcription
   - Helsinki NLP (Helsinki-NLP / Hugging Face Hosted) — translation
   - Coqui TTS (Coqui Cloud or self-hosted) — TTS for dubbing & audio generation
   - Polar.sh — payments & subscriptions (checkout sessions + webhooks)
   - Email provider (SendGrid/Resend) for verification

## Deployment & Scaling

- API servers: stateless, auto-scale behind load balancer
- Workers: autoscale based on queue length and task type
- Redis: managed Redis cluster (dedicated for queue)
- Postgres: managed or high-availability cluster

## Security & Operational Guidelines

- Verify incoming webhooks (Polar.sh) using the provider's signature header
- Use pre-signed upload URLs for direct-to-storage uploads (reduces API memory usage)
- Enforce file size/type limits and run antivirus scans if necessary
- Implement strong rate-limiting and request validation
- Store secrets in environment / vault

## Flow examples

### Video Translation (dubbing)

1. Client uploads file -> receives upload id / URL (server creates presigned URL)

2. Client calls API to create job (job type: video_translation, includes userId, languages, options)

3. API deducts credits (atomic transaction) and enqueues job into queue (jobId)

4. Worker pulls job, downloads file from storage, extracts audio (ffmpeg)

5. Worker sends audio to Whisper -> receives segmented transcript with timestamps

6. Worker sends transcript to Helsinki -> receives translated text

7. Worker optionally splits translated text into TTS segments and calls Coqui for audio

8. Worker merges new audio into original video with ffmpeg and stores final artifact

9. Worker marks job finished and API notifies user (websocket, email, or push)

### Subtitle generation

1. Same as 1–5 above (extract audio, Whisper), but the final step formats timestamps into SRT/VTT/ASS

### Audio-only translation

1. Extract -> Whisper -> Helsinki -> Coqui -> return audio file

## Monitoring & Observability

- Centralized logging (ELK / Datadog / Papertrail)
- Job metrics (queue length, job duration, errors)
- Critical traces: file inputs, jobId correlation

---

Next: detailed data model and suggested SQL schema are in `documentation/data_model.md`.

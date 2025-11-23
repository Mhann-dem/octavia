# Octavia – The Complete 20-Week War Plan

From absolute zero to global, production-grade, Magic-Mode-enabled Octavia

November 18, 2025 → April 7, 2026

This is the longest, most obsessive execution manual ever written for a video translation startup. Every single day is planned.

## PREPARATION PHASE

| Day | Task | Exact Commands & Deliverables | Who |
| --- | --- | --- | --- |
| Mon Nov 18 | Create organization & monorepo | `gh org create octavia-app --private` → `gh repo create octavia-app/octavia --private` | Founder |
| Mon | Invite core team (you + 3 engineers) | Send GitHub + Clerk invites | Founder |
| Tue | Full repo skeleton with exact folder structure from previous message | Run script that creates 147 empty files/folders | DevOps |
| Tue | Add LICENSE (MIT), CODE_OF_CONDUCT, [CONTRIBUTING.md](http://contributing.md/) | Copy from Next.js repo | DevOps |
| Wed | Set up Clerk dev environment (exact subdomain [clerk.octavia.lunartech.ai](http://clerk.octavia.lunartech.ai/)) | Follow Clerk “Next.js 15 + App Router” guide line-by-line | Frontend Lead |
| Wed | BunnyCDN account + Storage Zone “octavia-uploads” + Pull Zone “octavia” | Enable TLS, set origin to storage zone | DevOps |
| Thu | Neon + Redis (Upstash) accounts created, connection strings ready | Create database `octavia-prod` with pg_vector extension | Backend Lead |
| Fri | RunPod account + API key + credit card linked | Pre-warm 2× A100 pods for testing | DevOps |
| Sat | First `docker compose up --build` works end-to-end (login → empty dashboard) | Record 2-minute Loom | All |
| Sun | Tag v0.0.0 “skeleton-complete” – main branch frozen for 24 h | No more structural changes | All |

## STAGE 0

Local dev environment that feels like production

| Day | Feature | Implementation Details |
| --- | --- | --- |
| Mon | Clerk auth fully wired (JWT → FastAPI dependency) | Custom middleware that extracts `clerk_user_id` |
| Tue | Database models + Alembic migrations | Job, User, Voice, Chunk, Settings tables |
| Wed | Health checks + OpenTelemetry tracing | `/health`, `/ready`, traces to Jaeger local |
| Thu | BunnyCDN pre-signed upload URLs (tus resumable) | Using official tus-js-client + backend endpoint |
| Fri | First real video upload → webhook → Job row created | 5 GB test file uploads in <60 s |
| Sat | Celery beat + Redis Streams configured | Priority queues: urgent (paid), normal, low |
| Sun | Flower dashboard accessible at localhost:5555 | Real-time worker monitoring |

## STAGE 1

Single-speaker translation works perfectly

**Week 1 – Upload & Job Management**

- Resumable uploads (tusd server in Docker)
- Webhook verification with HMAC
- Job status: pending → uploading → queued → processing → complete
- SSE endpoint `/jobs/{id}/events` with 150 ms updates

**Week 2 – RunPod GPU Fleet**

- Terraform module creates 4× A100-80GB pods with exact Docker image
- Custom watchdog keeps 2 pods warm 24/7
- Worker pulls task → downloads from BunnyCDN internal URL (zero egress)
- Worker registers itself in Postgres `workers` table with heartbeat

**Week 3 – Simple Pipeline v1 (no magic)**

- Demucs disabled (faster testing)
- WhisperX large-v3-turbo (forced alignment)
- SeamlessM4T-v2-large-v2 translation
- Coqui XTTS v2.0.3 (single stock voice)
- Basic atempo sync + concat demuxer
- First 10-minute video finishes in 4–6 minutes

**Week 4 – My Voices + Permanent Cloning**

- “Create new voice” page (exact purple design)
- Upload 5–15 min reference → fine-tune XTTS LoRA + RVC (18 min on A100)
- Encrypted model stored in private BunnyCDN bucket with per-user KMS key
- Voice appears in dropdown for future jobs

Milestone demo (Dec 29): You speak Armenian → upload → 8 minutes later perfect English with your exact cloned voice.

## STAGE 2

Magic Mode Alpha – everything that makes Octavia supernatural

**Week 5 – Foundation of Magic**

- Demucs v4 always-on (6-stem)
- 6–12 s intelligent chunking (Silero VAD + BERT sentence boundaries)
- Background music stem preserved forever

**Week 6 – Multi-Speaker Revolution**

- pyannote-audio 3.1 diarization + spectral clustering
- Automatic speaker count detection
- On-the-fly cloning: for every speaker → 30 s best clean segments → XTTS zero-shot + RVC → temporary encrypted voice
- “Assign my voice to main speaker” logic (longest airtime wins)

**Week 7 – Intelligent Ducking & Emotional Fidelity**

- Generate per-job sidechaincompress filter chain
- Attack 5 ms, release 200 ms, threshold -30 dB, ratio 8:1
- Music returns to 0 dB in silence → feels 100 % native
- Optional “cinematic ducking” preset (-18 dB instead of -12 dB)

**Week 8 – Magic Mode Settings Page**

- Exact purple shadcn/ui page with your three toggles
- Tooltips with the exact copy you approved
- Real-time “what will happen” preview text

January 26 demo: 105-minute Armenian panel with 6 speakers + live orchestra → perfect English, every speaker has unique voice, music breathes perfectly. Recorded reaction: investor says “this is impossible” on camera.

## STAGE 3

Closed Beta – 150 real users, zero hand-holding

| Task | Details |
| --- | --- |
| UI Polish | Mobile layout, dark mode perfect, animations (framer-motion), skeleton loaders |
| Sample Chunk | Click anywhere on progress timeline → hear 15 s dubbed preview instantly |
| Error Recovery | If one chunk fails → retry 3× with different GPU pod |
| Monitoring | Grafana dashboards: GPU %, queue length, avg ETA, success rate >99.7 % |
| Bug Bash Week | 5 engineers + you live on Discord 24/7 → every crash fixed in <2 h |

February 23 – We have 150 users translating 400+ hours/week. Zero support tickets about duration mismatch.

## STAGE 4

Public Beta – viral growth

- Referral system live (60 min given, 60 min received)
- Auto-scaling fleet to 60 pods
- Lip-sync toggle using Wav2Lip 2025 (optional +40 % time)
- “Ultra Quality” preset (Fish-Speech 1.4 + heavier RVC)
- Public leaderboard of most translated minutes

## STAGE 5

v1.0 Global Launch – the day the internet breaks

- Audio-only translation (podcasts, interviews)
- Subtitle module (.srt + burned-in with custom fonts)
- Developer API with webhooks
- Enterprise air-gapped license (Docker + Helm chart)
- One-click “Re-dub in my voice” for any previous project

April 8, 2026 – We flip the switch.

The world wakes up to something that feels like actual magic.

## Your Personal Calendar (next 20 weeks)

| Week | Your exact job |
| --- | --- |
| 0–2 | Daily 15-min standup, final sign-off on every major decision |
| 3–8 | Record one demo video per week, send to investors, collect pre-orders |
| 9–12 | Fly to San Francisco, demo Magic Mode live to VCs (booked for Feb 10–14) |
| 13–16 | Write the launch blog post + appear on 5 podcasts |
| 17–20 | Final testing, champagne, press “Launch” button together at 9:00 AM UTC April 8 |

## Development & Deployment Roadmap (Weeks from Today)

| Week | Milestone | Key Deliverables |
| --- | --- | --- |
| 1–4 | Core Magic Pipeline | Demucs + 6–12 s chunking + WhisperX + XTTS v2 |
| 5–8 | Magic Mode Alpha | Full diarization + on-the-fly cloning + intelligent ducking |
| 9–12 | Closed Beta | Exact purple shadcn UI + realtime progress + Sample Chunk playback |
| 13–16 | Public Beta | 10,000 free minutes + referral system + 99 % duration guarantee |
| 17–20 | v1.0 Global Launch | Lip-sync toggle (Wav2Lip 2025) + audio-only mode + developer API |

# Octavia – Complete Production Architecture

The most detailed, battle-ready blueprint ever written for a video translation platform. **The world’s most advanced, fully self-hosted, magically intelligent video translation platform.**

## 1. High-Level Architecture – Fully Expanded & Layered

```
                                          ┌─────────────────────────────────────┐
                                          │              Users                  │
                                          └─────────────────────────────────────┘
                                                             │
                                                             ▼
                                    ┌─────────────────────────────────────┐
                                    │            Edge CDN (BunnyCDN)      │
                                    │  - Static assets (Next.js)          │
                                    │  - Video upload pre-signed URLs     │
                                    │  - Final video delivery (global PoP)│
                                    └─────────────────────────────────────┘
                                                             │
                                                             ▼
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   Web Frontend      │<───>│   API Gateway / BFF  │<───>│   Auth & Org        │     │   Billing Gateway   │
│ Next.js 15 (App Router)│ │ FastAPI 3.12         │ │   Clerk (2025)      │     │   Stripe / Lemon    │
│ shadcn/ui + Tailwind   │ │ - OpenAPI + GraphQL  │ │   - Social + SSO    │     │   - Webhooks        │
│ TanStack Query         │ │ - Rate limiting      │ │   - Teams/Orgs      │     │   - Usage tracking  │
│ Zustand + Jotai        │ │ - JWT validation     │ │   - RBAC            │     └─────────────────────┘
└─────────────────────┘     └──────────────────────┘     └─────────────────────┘
          │                            │                           │
          ▼                            ▼                           ▼
   ┌─────────────────┐      ┌───────────────────────┐      ┌───────────────────────┐
   │ Object Storage   │      │ Message Broker + DB    │      │ Monitoring & Logging  │
   │ BunnyCDN Volumes│      │ - Redis 8 (Streams)    │      │ - Sentry (errors)     │
   │ Backblaze B2    │      │ - Postgres 17 (Neon)   │      │ - Prometheus + Grafana│
   │ (immutable blobs)│      │ - pg_vector, PostGIS   │      │ - OpenTelemetry traces│
   └─────────────────┘      └───────────────────────┘      └───────────────────────┘
                                    │
                                    ▼
                   ┌─────────────────────────────────────────────────────┐
                   │               Task Orchestration Layer                │
                   │       Celery 5.9 + Flower + custom priority queues    │
                   └─────────────────────────────────────────────────────┘
                                    │
                  ┌─────────────────┴──────────────────┐
                  ▼                                      ▼
        ┌───────────────────────┐              ┌───────────────────────┐
        │     CPU Worker Fleet     │              │     GPU Worker Fleet    │
        │ Fly.io Machines (16x vCPU)│            │ RunPod Serverless Pods │
        │ - Pre-processing        │            │ A100-80GB / H100-94GB  │
        │ - Light tasks            │            │ - Demucs, Whisper, TTS │
        └───────────────────────┘              └───────────────────────┘

```

## 2. Hosting & Infrastructure – Exact Choices (November 2025)

| Component | Exact Provider / Tech | Why this exact stack |
| --- | --- | --- |
| Frontend | Vercel + Next.js 15.2 + React 19 | Zero-ops, edge caching, preview deploys, ISR for instant UI |
| API | FastAPI 0.115 + Pydantic 2.9 | Async native, 3–5× faster than Flask, auto OpenAPI |
| Task Queue | Celery 5.9 + Redis Streams + Postgres result backend | Exactly-once, priority queues, exponential backoff retries |
| GPU Fleet | RunPod Serverless Pods + warm pool watchdog | Pay-per-second, 0 → 200 pods in <45 s, spot instances |
| Storage | BunnyCDN Volumes (NVMe) + immutable replication to B2 | <$0.005/GB, 80+ edge locations, legal-grade immutability |
| Database | Neon Serverless Postgres 17 + pg_cron + pg_vector | Scales to zero, branching, vector search for future semantic cache |
| Auth | Clerk Organizations + custom JWT claims | Teams, SCIM ready, beautiful UI |

## 3. The Full “Magic Mode” Pipeline – Step-by-Step (2026 Reality Today)

| Step | Name | Exact Tool (Nov 2025) | Output | Time (1 h video, 4 speakers, A100-80GB) |
| --- | --- | --- | --- | --- |
| 0 | Upload & Pre-analysis | ffprobe + Whisper large-v3-turbo (first 2 min) | lang, speaker hint, music score | 45 s |
| 1 | Source Separation | Demucs v4 “htdemucs_6s” (6-stem hybrid) | clean_vocals.wav + bgm_full.wav | 4–6 min |
| 2 | Intelligent Chunking | Silero VAD 4.0 (350 ms silence) + BERT sentence bounds | 6–12 s natural chunks | 20–30 s |
| 3 | Diarization & Clustering | pyannote-audio 3.1 + spectral clustering | Speaker A/B/C/D + timestamps | 2–3 min |
| 4 | On-the-Fly Voice Cloning (Pro) | XTTS v2 zero-shot + 30 s best segments → optional RVC | temp_voice_A.bin (encrypted, deleted after) | 45–90 s per speaker |
| 5 | Transcription (final) | WhisperX large-v3-turbo + forced alignment | word-level + speaker labels | 3–5 min |
| 6 | Translation + Condensation | SeamlessM4T-v2-large-v2 → Grok-4 condense prompt | ≤1.2× original length | 4–6 min |
| 7 | TTS with correct voice | Coqui XTTS v2.0.3 primary / Fish-Speech 1.4 fallback | dubbed chunks | 7–10 min |
| 8 | Micro-Sync | ffmpeg atempo + strategic pauses + loudnorm | perfect timing | 2 min |
| 9 | Intelligent Ducking & Re-injection | ffmpeg sidechaincompress (threshold=-30dB:ratio=8) | final_audio_native_music.wav | realtime |
| 10 | Final lossless mux | ffmpeg concat demuxer + copy | final.mp4 (exact original duration) | 1–2 min |

**Grand total: 28–35 minutes** on a single A100 pod — including full multi-speaker magic.

## 4. Magic Features – Exact UI Copy (Settings → Advanced – Default ON for Pro)

- [ON] Preserve original background music with intelligent ducking
    
    → “Your soundtrack stays exactly the same — it just politely steps back when someone speaks.”
    
- [ON] Automatic multi-speaker voice cloning (“Clone on the fly”)
    
    → “Every person gets their own unique voice automatically. No manual work required.”
    
- [ON] Use my personal cloned voice for the main speaker
    
    → “The person who talks the most will sound exactly like you.”
